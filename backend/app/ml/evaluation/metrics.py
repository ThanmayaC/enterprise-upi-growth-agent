"""Model evaluation — one metric vocabulary for the whole platform.

Classification → accuracy, precision, recall, F1 (weighted), ROC AUC.
Regression     → RMSE, MAE, R².
Clustering     → silhouette score, Davies-Bouldin index.

Every evaluation is also persisted as JSON under ``artifacts/evaluation``
so training runs leave an auditable metrics trail.
"""

from __future__ import annotations

import json
from typing import Any

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    davies_bouldin_score,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
    roc_auc_score,
    silhouette_score,
)

from app.ml import config


def evaluate_classification(
    y_true: np.ndarray, y_pred: np.ndarray, proba: np.ndarray | None = None
) -> dict[str, float]:
    """Standard classification metrics (weighted for multi-class)."""

    metrics = {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, average="weighted",
                                           zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, average="weighted",
                                     zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, average="weighted",
                             zero_division=0)),
    }
    if proba is not None and len(np.unique(y_true)) > 1:
        try:
            if proba.ndim == 2 and proba.shape[1] == 2:
                metrics["roc_auc"] = float(roc_auc_score(y_true, proba[:, 1]))
            else:
                metrics["roc_auc"] = float(
                    roc_auc_score(y_true, proba, multi_class="ovr",
                                  average="weighted")
                )
        except ValueError:
            pass  # degenerate fold (a class missing from y_true)
    return {k: round(v, 4) for k, v in metrics.items()}


def evaluate_regression(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    """Standard regression metrics."""

    return {
        "rmse": round(float(np.sqrt(mean_squared_error(y_true, y_pred))), 4),
        "mae": round(float(mean_absolute_error(y_true, y_pred)), 4),
        "r2": round(float(r2_score(y_true, y_pred)), 4),
    }


def evaluate_clustering(x: np.ndarray, labels: np.ndarray) -> dict[str, float]:
    """Standard clustering quality metrics."""

    if len(np.unique(labels)) < 2:
        return {"silhouette": 0.0, "davies_bouldin": 0.0}
    return {
        "silhouette": round(float(silhouette_score(x, labels)), 4),
        "davies_bouldin": round(float(davies_bouldin_score(x, labels)), 4),
    }


def save_metrics(model_name: str, version: int, metrics: dict[str, Any]) -> None:
    """Persist an evaluation record to the artifacts trail."""

    config.ensure_dirs()
    path = config.EVAL_DIR / f"{model_name}_v{version:03d}.json"
    path.write_text(json.dumps(metrics, indent=2, default=str), encoding="utf-8")
