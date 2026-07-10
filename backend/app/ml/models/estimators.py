"""Estimator factories — configuration-driven scikit-learn model builders.

One factory per registered model name; hyper-parameters come exclusively
from :mod:`app.ml.config` (``MODEL_PARAMS``), so tuning never requires code
changes. Only scikit-learn estimators are used, per the frozen tech stack.
"""

from __future__ import annotations

from sklearn.base import BaseEstimator
from sklearn.cluster import KMeans
from sklearn.ensemble import (
    IsolationForest,
    RandomForestClassifier,
    RandomForestRegressor,
)

from app.ml import config


def _params(name: str) -> dict:
    return dict(config.MODEL_PARAMS.get(name, {}))


def make_regressor(name: str) -> RandomForestRegressor:
    """Random-forest regressor for a configured model name."""

    return RandomForestRegressor(random_state=config.RANDOM_STATE, **_params(name))


def make_classifier(name: str) -> RandomForestClassifier:
    """Random-forest classifier for a configured model name."""

    return RandomForestClassifier(random_state=config.RANDOM_STATE, **_params(name))


def make_kmeans(name: str) -> KMeans:
    """K-means clusterer for a configured model name."""

    return KMeans(random_state=config.RANDOM_STATE, **_params(name))


def make_isolation_forest(name: str) -> IsolationForest:
    """Isolation-forest anomaly detector for a configured model name."""

    return IsolationForest(random_state=config.RANDOM_STATE, **_params(name))


def make_estimator(name: str, task: str) -> BaseEstimator:
    """Dispatch a factory by task type (regression/classification/…)."""

    factory = {
        "regression": make_regressor,
        "classification": make_classifier,
        "clustering": make_kmeans,
        "anomaly": make_isolation_forest,
    }[task]
    return factory(name)
