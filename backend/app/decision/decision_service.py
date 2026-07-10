"""DecisionIntelligenceService — the platform's decision facade.

The single entry point Phase 12 consumers (AI Copilot, Report Generator,
Forecasting, Knowledge Engine) call for business decisions. Each use case:

    1. builds a RuleContext (Analytics facts + ML predictions + NPCI config),
    2. evaluates the relevant rule categories in priority order,
    3. maps the report to a final decision with combined confidence.

Every answer is a fully-dressed :class:`DecisionResult` dict — never a raw
ML prediction.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.decision.decision_context import DecisionContextBuilder
from app.decision.decision_engine import DecisionEngine, DecisionLabels
from app.decision.decision_result import DecisionResult
from app.rules import build_default_engine
from app.rules.npci_config import NpciRuleConfig

#: Verdict vocabularies per use case.
_ELIGIBILITY = DecisionLabels(
    approve="ELIGIBLE", conditional="ELIGIBLE_WITH_CONDITIONS",
    review="REVIEW_REQUIRED", reject="NOT_ELIGIBLE",
)
_RETRY = DecisionLabels(
    approve="RETRY_APPROVED", conditional="RETRY_WITH_CAUTION",
    review="MANUAL_REVIEW", reject="DO_NOT_RETRY",
)
_ENGAGEMENT = DecisionLabels(
    approve="STANDARD_ENGAGEMENT", conditional="TARGETED_INTERVENTION",
    review="RETENTION_REVIEW", reject="RETENTION_CRITICAL",
)


class DecisionIntelligenceService:
    """Decision use cases combining Analytics + ML + Business Rules."""

    def __init__(self, session: Session,
                 config_overrides: dict[str, Any] | None = None) -> None:
        self._config = NpciRuleConfig().with_overrides(config_overrides)
        self._contexts = DecisionContextBuilder(session, self._config)
        self._rules = build_default_engine()
        self._decisions = DecisionEngine()

    # ------------------------------------------------------------------
    # Use case 1 — Autopay eligibility (merchant)
    # ------------------------------------------------------------------
    def evaluate_autopay_eligibility(self, merchant_id: str) -> dict[str, Any]:
        """Should this merchant be onboarded to Autopay mandates?"""

        context = self._contexts.merchant_context(merchant_id)
        report = self._rules.evaluate(context, categories=(
            "validation", "compliance", "risk", "autopay",
            "eligibility", "recommendation",
        ))
        return self._decisions.decide(
            subject={"type": "merchant", "merchant_id": merchant_id,
                     "merchant_name": context.merchant["merchant_name"]},
            question="autopay_eligibility",
            context=context, report=report, labels=_ELIGIBILITY,
        ).to_dict()

    # ------------------------------------------------------------------
    # Use case 2 — Merchant priority
    # ------------------------------------------------------------------
    def evaluate_merchant_priority(self, merchant_id: str) -> dict[str, Any]:
        """Which investment priority tier does this merchant deserve?"""

        context = self._contexts.merchant_context(merchant_id)
        report = self._rules.evaluate(context, categories=(
            "validation", "risk", "merchant", "eligibility", "recommendation",
        ))
        score_rows = [r for r in report.results
                      if r.rule_name == "merchant_priority_score"]
        tier = (score_rows[0].evidence.get("priority_tier", "LOW")
                if score_rows else "LOW")
        return self._decisions.decide(
            subject={"type": "merchant", "merchant_id": merchant_id,
                     "merchant_name": context.merchant["merchant_name"]},
            question="merchant_priority",
            context=context, report=report, labels=_ELIGIBILITY,
            decision_override=f"{tier}_PRIORITY",
        ).to_dict()

    # ------------------------------------------------------------------
    # Use case 3 — Customer recommendation
    # ------------------------------------------------------------------
    def evaluate_customer_recommendation(self, customer_vpa: str) -> dict[str, Any]:
        """What is the right engagement strategy for this customer?"""

        # Scope: engagement is decided by customer/risk signals only.
        # Autopay eligibility is a different question (use case 1) — mixing
        # its blocking failures in here would mislabel healthy customers.
        context = self._contexts.customer_context(customer_vpa)
        report = self._rules.evaluate(context, categories=(
            "validation", "risk", "customer", "recommendation",
        ))
        return self._decisions.decide(
            subject={"type": "customer", "customer_vpa": customer_vpa},
            question="customer_recommendation",
            context=context, report=report, labels=_ENGAGEMENT,
        ).to_dict()

    # ------------------------------------------------------------------
    # Use case 4 — Transaction retry
    # ------------------------------------------------------------------
    def evaluate_transaction_retry(
        self, transaction: dict[str, Any], *, attempts: int = 0
    ) -> dict[str, Any]:
        """Should this failed transaction be retried automatically?"""

        context = self._contexts.transaction_context(
            transaction, attempts=attempts
        )
        report = self._rules.evaluate(context, categories=(
            "validation", "compliance", "risk", "retry", "recommendation",
        ))
        return self._decisions.decide(
            subject={"type": "transaction",
                     "transaction_id": transaction.get("transaction_id", "N/A")},
            question="transaction_retry",
            context=context, report=report, labels=_RETRY,
        ).to_dict()

    # ------------------------------------------------------------------
    # Introspection (Phase-12 documentation surfaces)
    # ------------------------------------------------------------------
    def rule_catalog(self) -> list[dict[str, Any]]:
        """Every registered rule with its identity and business meaning."""

        return [
            {"name": r.name, "category": r.category, "priority": r.priority,
             "description": r.description}
            for r in self._rules.rules()
        ]

    def active_configuration(self) -> dict[str, Any]:
        """The NPCI product configuration governing current decisions."""

        return self._config.to_dict()


def make_decision_result(**kwargs: Any) -> DecisionResult:
    """Convenience constructor re-export for Phase-12 consumers."""

    return DecisionResult(**kwargs)
