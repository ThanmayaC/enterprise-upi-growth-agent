"""Prediction explainability — no prediction leaves the platform naked.

Every prediction record carries:
    prediction, confidence, important features (name/value/importance),
    model name + version, and a human-readable reason sentence.

Technique (deliberately model-native, per the frozen stack):
    - tree ensembles → impurity feature importances, weighted by how far
      the row's value sits from the training median (a row-local signal);
    - K-means       → per-feature contribution to the distance from the
      assigned centroid;
    - IsolationForest → deviation of the row from training feature medians.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def top_features_supervised(
    estimator: Any, row: pd.Series, top_n: int
) -> list[dict[str, Any]]:
    """Rank features for a tree-ensemble prediction on one row.

    Importance is the model's global importance scaled by the row's
    absolute (non-zero) activation, so one-hot columns that are *off* for
    this row do not surface in its explanation.
    """

    importances = np.asarray(getattr(estimator, "feature_importances_", []))
    if importances.size == 0:
        return []
    values = row.to_numpy(dtype=float)
    active = (np.abs(values) > 1e-12).astype(float)
    local = importances * (0.25 + 0.75 * active)  # active features dominate
    order = np.argsort(local)[::-1][:top_n]
    return [
        {
            "feature": str(row.index[i]),
            "value": round(float(values[i]), 4),
            "importance": round(float(local[i]), 4),
        }
        for i in order
        if local[i] > 0
    ]


def top_features_cluster(
    centroid: np.ndarray, scaled_row: np.ndarray, names: list[str], top_n: int
) -> list[dict[str, Any]]:
    """Features contributing most to the sample's centroid distance."""

    contrib = (scaled_row - centroid) ** 2
    order = np.argsort(contrib)[::-1][:top_n]
    return [
        {
            "feature": names[i],
            "value": round(float(scaled_row[i]), 4),
            "importance": round(float(contrib[i]), 4),
        }
        for i in order
    ]


def top_features_anomaly(
    row: pd.Series, medians: dict[str, float], top_n: int
) -> list[dict[str, Any]]:
    """Features deviating most from their training medians."""

    deviations = []
    for name, value in row.items():
        base = medians.get(str(name), 0.0)
        scale = max(abs(base), 1.0)
        deviations.append((str(name), float(value), abs(float(value) - base) / scale))
    deviations.sort(key=lambda t: t[2], reverse=True)
    return [
        {"feature": n, "value": round(v, 4), "importance": round(d, 4)}
        for n, v, d in deviations[:top_n]
    ]


def build_reason(
    task: str, prediction: Any, confidence: float,
    features: list[dict[str, Any]], model_name: str,
) -> str:
    """One human-readable sentence per prediction."""

    drivers = ", ".join(f["feature"] for f in features[:3]) or "baseline signals"
    pct = f"{confidence * 100:.0f}%"
    if task == "classification":
        return (
            f"{model_name} assigned '{prediction}' with {pct} confidence, "
            f"driven mainly by {drivers}."
        )
    if task == "regression":
        return (
            f"{model_name} estimates {prediction} (ensemble agreement {pct}), "
            f"driven mainly by {drivers}."
        )
    if task == "clustering":
        return (
            f"{model_name} placed this entity in the '{prediction}' segment "
            f"(separation confidence {pct}); distinguishing signals: {drivers}."
        )
    return (
        f"{model_name} scored this observation as '{prediction}' "
        f"(normality confidence {pct}); strongest deviations: {drivers}."
    )
