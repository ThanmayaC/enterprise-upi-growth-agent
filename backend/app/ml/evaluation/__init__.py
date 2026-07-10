"""Evaluation: one metric vocabulary for the whole ML platform."""

from app.ml.evaluation.metrics import (
    evaluate_classification,
    evaluate_clustering,
    evaluate_regression,
)

__all__ = [
    "evaluate_classification",
    "evaluate_clustering",
    "evaluate_regression",
]
