"""Central ML configuration — the single source of truth for the ML layer.

Purpose:
    Keep every tunable (period splits, sample caps, hyper-parameters,
    category thresholds, artifact locations) in one configuration-driven
    place so trainers, feature transformers, and the prediction engine never
    hard-code magic numbers. Changing a training window or a model's depth is
    a one-line edit here.

Design notes:
    - Periods use real calendar dates verified against the dataset
      (2024-01-01 … 2025-01-04). Features come from the first half of 2024,
      labels from the second half, so every supervised target is a genuine
      out-of-window outcome (no leakage).
    - The ML layer consumes only the Analytics and Service layers; it never
      touches SQL, repositories, or ORM models.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

# --- Artifact locations ------------------------------------------------------
ML_DIR: Path = Path(__file__).resolve().parent
ARTIFACTS_DIR: Path = ML_DIR / "artifacts"
MODELS_DIR: Path = ARTIFACTS_DIR / "models"
REGISTRY_PATH: Path = ARTIFACTS_DIR / "registry.json"
EVAL_DIR: Path = ARTIFACTS_DIR / "evaluation"

# --- Reproducibility ---------------------------------------------------------
RANDOM_STATE: int = 42
TEST_SIZE: float = 0.25

# --- Temporal split (feature window vs. label window) ------------------------
FEATURE_START: date = date(2024, 1, 1)
FEATURE_MID: date = date(2024, 3, 31)     # feature window sub-split (p1 | p2)
FEATURE_END: date = date(2024, 6, 30)
LABEL_START: date = date(2024, 7, 1)
LABEL_MID: date = date(2024, 9, 30)       # inference window sub-split (p1 | p2)
LABEL_END: date = date(2024, 12, 31)
FULL_START: date | None = None
FULL_END: date | None = None

# --- Autopay observation windows (features strictly precede labels) ----------
AUTOPAY_FEATURE_WINDOW: tuple[date, date] = (date(2024, 6, 1), date(2024, 6, 30))
AUTOPAY_FEATURE_LIMIT: int = 80_000
AUTOPAY_LABEL_WINDOW: tuple[date, date] = (date(2024, 7, 1), date(2024, 8, 31))
AUTOPAY_LABEL_LIMIT: int = 120_000

# --- Label-side fetch cap (H2 active customer universe ≈ 132k) ---------------
CUSTOMER_LABEL_LIMIT: int = 200_000

# --- Sampling caps (keep training bounded & fast at fact-table scale) --------
CUSTOMER_SAMPLE_LIMIT: int = 40_000
CUSTOMER_SEGMENT_LIMIT: int = 30_000
TXN_SAMPLE_START: date = date(2024, 6, 1)
TXN_SAMPLE_END: date = date(2024, 6, 30)
TXN_SAMPLE_LIMIT: int = 60_000

# --- Business-labelled category thresholds -----------------------------------
#: Merchant growth categories by period-over-period transaction growth (%).
GROWTH_CATEGORY_BINS: list[tuple[float, str]] = [
    (-10.0, "Declining"),
    (10.0, "Stable"),
    (50.0, "Growing"),
    (float("inf"), "High Growth"),
]

#: Customer activity levels by label-period transaction count.
ACTIVITY_LEVEL_BINS: list[tuple[float, str]] = [
    (0.5, "Dormant"),
    (3.0, "Occasional"),
    (10.0, "Regular"),
    (float("inf"), "Power"),
]

#: Cluster label vocabularies (assigned by centroid ranking, see trainers).
MERCHANT_SEGMENTS: list[str] = ["Declining", "Stable", "Emerging", "High Growth"]
CUSTOMER_SEGMENTS: list[str] = ["Dormant", "Occasional", "Regular", "Power"]

# --- Model hyper-parameters (per registered model) ---------------------------
MODEL_PARAMS: dict[str, dict[str, Any]] = {
    "merchant_growth_regressor": {
        "n_estimators": 200, "max_depth": 8, "min_samples_leaf": 3,
    },
    "merchant_growth_classifier": {
        "n_estimators": 200, "max_depth": 8, "min_samples_leaf": 3,
        "class_weight": "balanced",
    },
    "customer_retention": {
        "n_estimators": 160, "max_depth": 10, "min_samples_leaf": 5,
        "class_weight": "balanced",
    },
    "customer_expected_usage": {
        "n_estimators": 160, "max_depth": 10, "min_samples_leaf": 5,
    },
    "customer_activity_level": {
        "n_estimators": 160, "max_depth": 10, "min_samples_leaf": 5,
        "class_weight": "balanced",
    },
    "transaction_success": {
        "n_estimators": 150, "max_depth": 12, "min_samples_leaf": 20,
        "class_weight": "balanced", "n_jobs": -1,
    },
    "merchant_autopay": {
        "n_estimators": 160, "max_depth": 8, "min_samples_leaf": 4,
        "class_weight": "balanced",
    },
    "customer_autopay": {
        "n_estimators": 160, "max_depth": 10, "min_samples_leaf": 5,
        "class_weight": "balanced",
    },
    "merchant_segmentation": {"n_clusters": 4, "n_init": 10},
    "customer_segmentation": {"n_clusters": 4, "n_init": 10},
    "anomaly_detector": {"n_estimators": 150, "contamination": 0.06},
}

#: Number of important features surfaced in every explanation.
TOP_FEATURES: int = 5


def ensure_dirs() -> None:
    """Create the artifact directories if they do not yet exist."""

    for path in (ARTIFACTS_DIR, MODELS_DIR, EVAL_DIR):
        path.mkdir(parents=True, exist_ok=True)
