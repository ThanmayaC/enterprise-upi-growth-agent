"""MLIntelligenceService — the clean facade Phase 12 (API layer) consumes.

Composes dataset builders (inference mode) with the prediction engine and
returns plain, JSON-ready dicts shaped for the future React surfaces:
prediction cards, confidence indicators, forecast/trend charts, and anomaly
timelines. The API layer will only ever need this one class.

Dependency direction is preserved: this module sits at the top of the ML
layer and reaches *down* into Analytics/Services through the data provider —
never sideways into routers or the frontend.
"""

from __future__ import annotations

from typing import Any

import pandas as pd
from sqlalchemy.orm import Session

from app.ml.datasets.builders import (
    CustomerDatasetBuilder,
    MerchantDatasetBuilder,
    TimeSeriesDatasetBuilder,
    TransactionDatasetBuilder,
)
from app.ml.datasets.data_provider import MLDataProvider
from app.ml.prediction.prediction_engine import PredictionEngine
from app.ml.registry.model_registry import ModelRegistry


class MLIntelligenceService:
    """Serve every Phase-11 model through one API-ready interface."""

    def __init__(self, session: Session,
                 engine: PredictionEngine | None = None) -> None:
        provider = MLDataProvider(session)
        self._merchants = MerchantDatasetBuilder(provider)
        self._customers = CustomerDatasetBuilder(provider)
        self._transactions = TransactionDatasetBuilder(provider)
        self._timeseries = TimeSeriesDatasetBuilder(provider)
        self._engine = engine or PredictionEngine()

    # ------------------------------------------------------------------
    # Registry / metadata surfaces
    # ------------------------------------------------------------------
    def model_catalog(self) -> list[dict[str, Any]]:
        """All registered model versions with status, metrics, lineage."""

        registry = ModelRegistry()
        return [
            {
                "name": r.name, "version": r.version, "task": r.task,
                "status": r.status, "trained_at": r.trained_at,
                "metrics": r.metrics, "description": r.description,
                "feature_count": len(r.features),
            }
            for r in registry.list_models()
        ]

    # ------------------------------------------------------------------
    # Merchant intelligence
    # ------------------------------------------------------------------
    def merchant_growth_predictions(
        self, *, top_n: int | None = None, merchant_id: str | None = None
    ) -> list[dict[str, Any]]:
        """Expected growth %, category, confidence — per merchant."""

        ds = self._merchants.inference()
        frame, ids = self._select(ds.frame, ds.ids, "merchant_id", merchant_id)
        reg = self._engine.predict("merchant_growth_regressor", frame, ids)
        clf = self._engine.predict("merchant_growth_classifier", frame, ids)
        names = frame["merchant_name"].tolist()
        rows = [
            {
                "merchant_id": r["id"],
                "merchant_name": names[i],
                "expected_growth_pct": r["prediction"],
                "growth_category": clf[i]["prediction"],
                "category_probabilities": clf[i]["probabilities"],
                "confidence": r["confidence"],
                "category_confidence": clf[i]["confidence"],
                "important_features": r["important_features"],
                "model": r["model"], "version": r["version"],
                "reason": r["reason"],
            }
            for i, r in enumerate(reg)
        ]
        rows.sort(key=lambda r: r["expected_growth_pct"], reverse=True)
        return rows[:top_n] if top_n else rows

    def merchant_segments(self) -> list[dict[str, Any]]:
        """Business segment per merchant (High Growth / Stable / …)."""

        ds = self._merchants.inference()
        return self._engine.predict("merchant_segmentation", ds.frame, ds.ids)

    # ------------------------------------------------------------------
    # Customer intelligence
    # ------------------------------------------------------------------
    def customer_behaviour_predictions(
        self, *, top_n: int | None = None, customer_vpa: str | None = None
    ) -> list[dict[str, Any]]:
        """Activity level, expected usage, retention — per customer."""

        ds = self._customers.inference()
        frame, ids = self._select(ds.frame, ds.ids, "customer_vpa", customer_vpa)
        usage = self._engine.predict("customer_expected_usage", frame, ids)
        level = self._engine.predict("customer_activity_level", frame, ids)
        retention = self._engine.predict("customer_retention", frame, ids)
        rows = [
            {
                "customer_vpa": r["id"],
                "expected_usage": max(r["prediction"], 0.0),
                "activity_level": level[i]["prediction"],
                "activity_probabilities": level[i]["probabilities"],
                "retention_probability": retention[i]["probabilities"].get("1", 0.0),
                "confidence": r["confidence"],
                "important_features": r["important_features"],
                "model": r["model"], "version": r["version"],
                "reason": r["reason"],
            }
            for i, r in enumerate(usage)
        ]
        rows.sort(key=lambda r: r["expected_usage"], reverse=True)
        return rows[:top_n] if top_n else rows

    def customer_segments(self, *, sample: int | None = 5_000) -> list[dict[str, Any]]:
        """Business segment per customer (Power / Regular / …), sampled."""

        ds = self._customers.inference()
        frame, ids = ds.frame, ds.ids
        if sample is not None and len(frame) > sample:
            frame = frame.sample(n=sample, random_state=0).reset_index(drop=True)
            ids = frame["customer_vpa"]
        return self._engine.predict("customer_segmentation", frame, ids)

    # ------------------------------------------------------------------
    # Transaction intelligence
    # ------------------------------------------------------------------
    def transaction_success_prediction(
        self, transaction: dict[str, Any]
    ) -> dict[str, Any]:
        """Success/failure probability for one prospective transaction."""

        frame = self._transactions.inference_frame([transaction])
        row = self._engine.predict_single("transaction_success", frame)
        proba = row["probabilities"]
        row["probability_success"] = proba.get("1", 0.0)
        row["probability_failure"] = proba.get("0", 0.0)
        row["prediction"] = (
            "SUCCESS" if row["probability_success"] >= 0.5 else "FAILURE"
        )
        return row

    # ------------------------------------------------------------------
    # Autopay opportunity intelligence
    # ------------------------------------------------------------------
    def autopay_opportunities(
        self, *, top_n: int = 20
    ) -> dict[str, list[dict[str, Any]]]:
        """Ranked merchant and customer Autopay opportunity scores."""

        m_ds = self._merchants.inference()
        merchant_rows = self._engine.predict("merchant_autopay", m_ds.frame, m_ds.ids)
        m_names = m_ds.frame["merchant_name"].tolist()
        merchants = [
            {
                "merchant_id": r["id"],
                "merchant_name": m_names[i],
                "opportunity_score": round(
                    100.0 * r["probabilities"].get("1", 0.0), 2
                ),
                "adoption_probability": r["probabilities"].get("1", 0.0),
                "confidence": r["confidence"],
                "important_features": r["important_features"],
                "model": r["model"], "version": r["version"],
                "reason": r["reason"],
            }
            for i, r in enumerate(merchant_rows)
        ]
        merchants.sort(key=lambda r: r["opportunity_score"], reverse=True)

        c_ds = self._customers.inference()
        customer_rows = self._engine.predict("customer_autopay", c_ds.frame, c_ds.ids)
        customers = [
            {
                "customer_vpa": r["id"],
                "opportunity_score": round(
                    100.0 * r["probabilities"].get("1", 0.0), 2
                ),
                "adoption_probability": r["probabilities"].get("1", 0.0),
                "confidence": r["confidence"],
                "important_features": r["important_features"],
                "model": r["model"], "version": r["version"],
                "reason": r["reason"],
            }
            for r in customer_rows
        ]
        customers.sort(key=lambda r: r["opportunity_score"], reverse=True)
        return {
            "merchants": merchants[:top_n],
            "customers": customers[:top_n],
        }

    # ------------------------------------------------------------------
    # Anomaly intelligence
    # ------------------------------------------------------------------
    def detect_anomalies(self) -> list[dict[str, Any]]:
        """Daily anomaly timeline (volume / failure spike / growth)."""

        ds = self._timeseries.anomaly_training()
        rows = self._engine.predict("anomaly_detector", ds.frame, ds.ids)
        return [r for r in rows]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _select(
        frame: pd.DataFrame, ids: pd.Series, key: str, value: str | None
    ) -> tuple[pd.DataFrame, pd.Series]:
        """Optionally narrow an inference frame to one entity."""

        if value is None:
            return frame, ids
        mask = frame[key].astype(str) == str(value)
        subset = frame[mask].reset_index(drop=True)
        if subset.empty:
            raise KeyError(f"{key}={value!r} not present in the inference window")
        return subset, subset[key]
