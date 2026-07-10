"""Decision context assembly — gathers Analytics + ML facts for a subject.

This is the Decision layer's data boundary: it reaches *down* into the ML
layer's public surfaces (``MLIntelligenceService``, ``PredictionEngine``,
dataset builders, ``MLDataProvider``) and packages what the rules need
into a :class:`RuleContext`. No SQL, no repositories, no ORM — the same
discipline the ML layer already enforces.
"""

from __future__ import annotations

from typing import Any

import pandas as pd
from sqlalchemy.orm import Session

from app.ml.datasets.builders import (
    CustomerDatasetBuilder,
    MerchantDatasetBuilder,
)
from app.ml.datasets.data_provider import MLDataProvider
from app.ml.prediction.prediction_engine import PredictionEngine
from app.ml.prediction.prediction_service import MLIntelligenceService
from app.rules.npci_config import NpciRuleConfig
from app.rules.rule_context import RuleContext
from app.rules.rule_result import RuleResult


class DecisionContextBuilder:
    """Build rule contexts for merchants, customers, and transactions."""

    def __init__(self, session: Session, config: NpciRuleConfig) -> None:
        self._config = config
        self._ml = MLIntelligenceService(session)
        self._engine = PredictionEngine()
        provider = MLDataProvider(session)
        self._merchants = MerchantDatasetBuilder(provider)
        self._customers = CustomerDatasetBuilder(provider)

    # ------------------------------------------------------------------
    # Merchant context
    # ------------------------------------------------------------------
    def merchant_context(self, merchant_id: str) -> RuleContext:
        """Analytics + growth/autopay predictions for one merchant."""

        frame = self._merchants.inference_frame()
        row = frame[frame["merchant_id"].astype(str) == str(merchant_id)]
        if row.empty:
            raise KeyError(f"merchant {merchant_id!r} not found in the "
                           f"current analysis window")
        row = row.reset_index(drop=True)
        merchant = self._merchant_facts(row)

        growth = self._ml.merchant_growth_predictions(merchant_id=merchant_id)[0]
        autopay = self._engine.predict(
            "merchant_autopay", row, row["merchant_id"]
        )[0]
        autopay["adoption_probability"] = autopay["probabilities"].get("1", 0.0)

        return RuleContext(
            config=self._config,
            merchant=merchant,
            predictions={"merchant_growth": growth,
                         "merchant_autopay": autopay},
            analytics={"merchant_traffic": merchant},
        )

    # ------------------------------------------------------------------
    # Customer context
    # ------------------------------------------------------------------
    def customer_context(self, customer_vpa: str) -> RuleContext:
        """Activity analytics + behaviour/autopay predictions for a customer."""

        frame = self._customers.inference_frame()
        row = frame[frame["customer_vpa"].astype(str) == str(customer_vpa)]
        if row.empty:
            raise KeyError(f"customer {customer_vpa!r} not active in the "
                           f"current analysis window")
        row = row.reset_index(drop=True)
        customer = self._customer_facts(row)

        behaviour = self._ml.customer_behaviour_predictions(
            customer_vpa=customer_vpa
        )[0]
        autopay = self._engine.predict(
            "customer_autopay", row, row["customer_vpa"]
        )[0]
        autopay["adoption_probability"] = autopay["probabilities"].get("1", 0.0)

        return RuleContext(
            config=self._config,
            customer=customer,
            predictions={"customer_behaviour": behaviour,
                         "customer_autopay": autopay},
            analytics={"customer_activity": customer},
        )

    # ------------------------------------------------------------------
    # Transaction context
    # ------------------------------------------------------------------
    def transaction_context(
        self, transaction: dict[str, Any], *, attempts: int = 0
    ) -> RuleContext:
        """Success prediction + caller-supplied facts for one transaction."""

        prediction = self._ml.transaction_success_prediction(dict(transaction))
        return RuleContext(
            config=self._config,
            transaction=dict(transaction),
            predictions={"transaction_success": prediction},
            analytics={},
            extras={"attempts": attempts},
        )

    # ------------------------------------------------------------------
    # Fact extraction helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _merchant_facts(row: pd.DataFrame) -> dict[str, Any]:
        r = row.iloc[0]
        total_txns = float(r["total_transactions"])
        total_amount = float(r["total_amount"])
        return {
            "merchant_id": str(r["merchant_id"]),
            "merchant_name": str(r["merchant_name"]),
            "mcc_code": str(r["mcc_code"]),
            "total_transactions": int(total_txns),
            "total_amount": round(total_amount, 2),
            "success_rate": float(r["success_rate"]),
            "avg_ticket": round(total_amount / total_txns, 2) if total_txns else 0.0,
            "mcc_autopay_share": float(r.get("mcc_autopay_share", 0.0)),
        }

    @staticmethod
    def _customer_facts(row: pd.DataFrame) -> dict[str, Any]:
        r = row.iloc[0]
        p1, p2 = float(r["p1_count"]), float(r["p2_count"])
        total = p1 + p2
        autopay_txns = float(r.get("autopay_txns", 0.0))
        return {
            "customer_vpa": str(r["customer_vpa"]),
            "window_transactions": int(total),
            "window_amount": round(float(r["p1_amount"]) + float(r["p2_amount"]), 2),
            "early_count": int(p1),
            "late_count": int(p2),
            "autopay_txns": int(autopay_txns),
            "autopay_share": round(autopay_txns / total, 4) if total else 0.0,
        }


def used_predictions(context: RuleContext) -> dict[str, Any]:
    """Compact provenance view of the predictions a decision consumed."""

    return {
        key: {
            "prediction": rec.get("prediction",
                                  rec.get("expected_growth_pct",
                                          rec.get("expected_usage"))),
            "confidence": rec.get("confidence"),
            "model": rec.get("model"),
            "version": rec.get("version"),
        }
        for key, rec in context.predictions.items()
    }


def rule_evidence(results: list[RuleResult]) -> dict[str, Any]:
    """Merged evidence of all decisive rule results (audit trail)."""

    return {r.rule_name: r.evidence for r in results if r.evidence}
