"""Prediction engine — single and batch inference for every registered model.

The engine loads a model's self-contained bundle from the registry (cached),
pushes raw domain frames through the *fitted* transformer stored with the
model (zero train/serve skew), and emits fully-dressed prediction records:

    {id, prediction, probabilities?, confidence, important_features,
     model, version, reason}

Task-specific outputs:
    classification → class probabilities + winning-class confidence
    regression     → point estimate + ensemble-agreement confidence
    clustering     → business segment + centroid-separation confidence
    anomaly        → normal/anomaly flag, anomaly type, normality confidence
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from app.ml import config
from app.ml.explainability.explainer import (
    build_reason,
    top_features_anomaly,
    top_features_cluster,
    top_features_supervised,
)
from app.ml.registry.model_registry import ModelRegistry
from app.ml.utils.confidence import (
    anomaly_confidence,
    classification_confidence,
    cluster_confidence,
    regression_confidence,
)

#: Anomaly typing rules: feature → business anomaly type.
ANOMALY_TYPES = {
    "failure_vs_baseline": "Failure spike",
    "failure_rate_pct": "Failure spike",
    "failure_count": "Failure spike",
    "dod_growth_pct": "Growth anomaly",
    "count_vs_baseline": "Volume anomaly",
    "transaction_count": "Volume anomaly",
    "log_amount": "Volume anomaly",
}


class PredictionEngine:
    """Serve any registered model, one row or in batch."""

    def __init__(self, registry: ModelRegistry | None = None) -> None:
        self._registry = registry or ModelRegistry()
        self._cache: dict[str, tuple[Any, dict[str, Any]]] = {}

    # ------------------------------------------------------------------
    # Bundle access
    # ------------------------------------------------------------------
    def _bundle(self, name: str) -> tuple[Any, dict[str, Any]]:
        if name not in self._cache:
            self._cache[name] = self._registry.load_active(name)
        return self._cache[name]

    def model_info(self, name: str) -> dict[str, Any]:
        """Registry metadata for one model (for API surfaces)."""

        record, _ = self._bundle(name)
        return {
            "model": record.name,
            "version": record.version,
            "task": record.task,
            "trained_at": record.trained_at,
            "metrics": record.metrics,
            "description": record.description,
        }

    # ------------------------------------------------------------------
    # Prediction
    # ------------------------------------------------------------------
    def predict(
        self, name: str, frame: pd.DataFrame, ids: pd.Series | None = None
    ) -> list[dict[str, Any]]:
        """Batch prediction over a raw domain frame."""

        record, bundle = self._bundle(name)
        transformer = bundle["transformer"]
        x = transformer.transform(frame)
        id_values = (
            ids.reset_index(drop=True)
            if ids is not None
            else pd.Series(range(len(x)))
        )

        task = bundle["task"]
        if task == "classification":
            rows = self._classify(bundle, x)
        elif task == "regression":
            rows = self._regress(bundle, x)
        elif task == "clustering":
            rows = self._cluster(bundle, x)
        else:
            rows = self._anomaly(bundle, x)

        for i, row in enumerate(rows):
            row["id"] = id_values.iloc[i] if i < len(id_values) else i
            row["model"] = record.name
            row["version"] = record.version
            row["reason"] = build_reason(
                task, row["prediction"], row["confidence"],
                row["important_features"], record.name,
            )
        return rows

    def predict_single(self, name: str, payload: dict[str, Any] |
                       pd.DataFrame) -> dict[str, Any]:
        """Single prediction from one raw domain row."""

        frame = (
            payload.copy()
            if isinstance(payload, pd.DataFrame)
            else pd.DataFrame([payload])
        )
        return self.predict(name, frame)[0]

    # ------------------------------------------------------------------
    # Task branches
    # ------------------------------------------------------------------
    @staticmethod
    def _classify(bundle: dict[str, Any], x: pd.DataFrame) -> list[dict[str, Any]]:
        model = bundle["estimator"]
        proba = model.predict_proba(x)
        classes = [str(c) for c in model.classes_]
        out = []
        for i in range(len(x)):
            winner = int(np.argmax(proba[i]))
            out.append({
                "prediction": classes[winner],
                "probabilities": {
                    classes[j]: round(float(proba[i, j]), 4)
                    for j in range(len(classes))
                },
                "confidence": classification_confidence(proba[i]),
                "important_features": top_features_supervised(
                    model, x.iloc[i], config.TOP_FEATURES
                ),
            })
        return out

    @staticmethod
    def _regress(bundle: dict[str, Any], x: pd.DataFrame) -> list[dict[str, Any]]:
        model = bundle["estimator"]
        preds = model.predict(x)
        per_tree = np.stack([t.predict(x.to_numpy()) for t in model.estimators_])
        out = []
        for i in range(len(x)):
            out.append({
                "prediction": round(float(preds[i]), 4),
                "probabilities": None,
                "confidence": regression_confidence(per_tree[:, i]),
                "important_features": top_features_supervised(
                    model, x.iloc[i], config.TOP_FEATURES
                ),
            })
        return out

    @staticmethod
    def _cluster(bundle: dict[str, Any], x: pd.DataFrame) -> list[dict[str, Any]]:
        model = bundle["estimator"]
        scaler = bundle["scaler"]
        segment_map: dict[int, str] = bundle["segment_map"]
        names = bundle["feature_names"]
        x_scaled = scaler.transform(x)
        distances = model.transform(x_scaled)
        assignments = model.predict(x_scaled)
        out = []
        for i in range(len(x)):
            cluster = int(assignments[i])
            centroid = model.cluster_centers_[cluster]
            out.append({
                "prediction": segment_map.get(cluster, f"Segment {cluster}"),
                "probabilities": None,
                "confidence": cluster_confidence(distances[i]),
                "important_features": top_features_cluster(
                    centroid, x_scaled[i], names, config.TOP_FEATURES
                ),
                "cluster": cluster,
            })
        return out

    @staticmethod
    def _anomaly(bundle: dict[str, Any], x: pd.DataFrame) -> list[dict[str, Any]]:
        model = bundle["estimator"]
        scaler = bundle["scaler"]
        lo, hi = bundle["score_range"]
        medians = bundle["feature_medians"]
        x_scaled = scaler.transform(x)
        scores = model.decision_function(x_scaled)
        flags = model.predict(x_scaled)
        out = []
        for i in range(len(x)):
            is_anomaly = bool(flags[i] == -1)
            features = top_features_anomaly(x.iloc[i], medians, config.TOP_FEATURES)
            anomaly_type = None
            if is_anomaly and features:
                anomaly_type = ANOMALY_TYPES.get(
                    features[0]["feature"], "Volume anomaly"
                )
            out.append({
                "prediction": "ANOMALY" if is_anomaly else "NORMAL",
                "probabilities": None,
                "confidence": anomaly_confidence(float(scores[i]), lo, hi),
                "important_features": features,
                "is_anomaly": is_anomaly,
                "anomaly_type": anomaly_type,
                "score": round(float(scores[i]), 4),
            })
        return out
