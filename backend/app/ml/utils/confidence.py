"""Confidence scoring for every prediction task.

Purpose:
    A single, defensible definition of "confidence" per model family, so no
    prediction is ever returned without one:
      - classification → the winning class probability,
      - regression (ensemble) → agreement across the ensemble's trees,
      - clustering → separation between the nearest and next-nearest centroid,
      - anomaly → normalized isolation score.
"""

from __future__ import annotations

import numpy as np


def classification_confidence(proba_row: np.ndarray) -> float:
    """Confidence = probability mass on the predicted class."""

    return round(float(np.max(proba_row)), 4)


def regression_confidence(tree_predictions: np.ndarray) -> float:
    """Confidence from ensemble agreement for one sample.

    Parameters:
        tree_predictions: 1-D array of the per-tree predictions for a sample.

    Returns:
        ``1 / (1 + coefficient_of_variation)`` in [0, 1]; high when the trees
        agree, low when they disagree.
    """

    preds = np.asarray(tree_predictions, dtype=float)
    mean = float(np.mean(preds))
    std = float(np.std(preds))
    denom = abs(mean) if abs(mean) > 1e-9 else 1.0
    cv = std / denom
    return round(float(1.0 / (1.0 + cv)), 4)


def cluster_confidence(distances: np.ndarray) -> float:
    """Confidence from centroid separation for one sample.

    Parameters:
        distances: distances from the sample to every cluster centroid.

    Returns:
        ``1 - nearest/second_nearest`` in [0, 1]; high when the point sits
        clearly inside one cluster.
    """

    ordered = np.sort(np.asarray(distances, dtype=float))
    if len(ordered) < 2 or ordered[1] == 0:
        return 1.0
    return round(float(1.0 - ordered[0] / ordered[1]), 4)


def anomaly_confidence(score: float, min_score: float, max_score: float) -> float:
    """Map an IsolationForest score into a [0, 1] confidence of normality."""

    if max_score - min_score < 1e-9:
        return 0.5
    return round(float((score - min_score) / (max_score - min_score)), 4)
