"""Trainer specifications — the declarative catalog of every ML model.

A :class:`TrainerSpec` describes *what* to train (dataset, target,
transformer, task, business meaning); the generic
:class:`~app.ml.pipelines.training_pipeline.TrainingPipeline` owns *how*
(split → fit → evaluate → persist → register). Adding a model to the
platform means adding one spec here — nothing else changes.

Catalog (11 registered models across the 7 required capabilities):
    1. merchant_growth_regressor    — expected growth %% (regression)
    2. merchant_growth_classifier   — growth category (classification)
    3. customer_expected_usage      — H2 usage count (regression)
    4. customer_activity_level      — activity level (classification)
    5. customer_retention           — retention probability (classification)
    6. transaction_success          — success probability (classification)
    7. merchant_autopay             — merchant adoption probability
    8. customer_autopay             — customer adoption probability
    9. merchant_segmentation        — K-means segments (clustering)
    10. customer_segmentation       — K-means segments (clustering)
    11. anomaly_detector            — daily volume/failure/growth anomalies
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import pandas as pd

from app.ml import config
from app.ml.datasets.builders import (
    CustomerDatasetBuilder,
    MerchantDatasetBuilder,
    MLDataset,
    TimeSeriesDatasetBuilder,
    TransactionDatasetBuilder,
)
from app.ml.datasets.data_provider import MLDataProvider
from app.ml.feature_engineering.base import BaseFeatureTransformer
from app.ml.feature_engineering.customer_features import CustomerFeatureTransformer
from app.ml.feature_engineering.merchant_features import MerchantFeatureTransformer
from app.ml.feature_engineering.time_features import DailySeriesFeatureTransformer
from app.ml.feature_engineering.transaction_features import (
    TransactionFeatureTransformer,
)


@dataclass
class BuilderSet:
    """All dataset builders wired to one shared (memoizing) provider."""

    merchant: MerchantDatasetBuilder
    customer: CustomerDatasetBuilder
    transaction: TransactionDatasetBuilder
    timeseries: TimeSeriesDatasetBuilder

    @classmethod
    def from_provider(cls, provider: MLDataProvider) -> "BuilderSet":
        return cls(
            merchant=MerchantDatasetBuilder(provider),
            customer=CustomerDatasetBuilder(provider),
            transaction=TransactionDatasetBuilder(provider),
            timeseries=TimeSeriesDatasetBuilder(provider),
        )


@dataclass
class PreparedData:
    """Everything the pipeline needs to train one model."""

    dataset: MLDataset
    transformer: BaseFeatureTransformer
    y: pd.Series | None = None
    #: clustering only — segment vocabulary, worst → best
    segment_labels: list[str] | None = None
    #: clustering only — raw-frame column used to rank centroids
    order_column: str | None = None


@dataclass
class TrainerSpec:
    """One trainable model: identity, business meaning, and data recipe."""

    name: str
    task: str  # regression | classification | clustering | anomaly
    description: str
    prepare: Callable[[BuilderSet], PreparedData]
    tags: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Prepare functions (thin: builders + transformers do the real work)
# ---------------------------------------------------------------------------
def _merchant_growth_reg(b: BuilderSet) -> PreparedData:
    ds = b.merchant.growth_training()
    return PreparedData(ds, MerchantFeatureTransformer(), y=ds.targets["growth_pct"])


def _merchant_growth_clf(b: BuilderSet) -> PreparedData:
    ds = b.merchant.growth_training()
    return PreparedData(
        ds, MerchantFeatureTransformer(), y=ds.targets["growth_category"]
    )


def _customer_usage(b: BuilderSet) -> PreparedData:
    ds = b.customer.behaviour_training()
    return PreparedData(ds, CustomerFeatureTransformer(), y=ds.targets["expected_usage"])


def _customer_activity(b: BuilderSet) -> PreparedData:
    ds = b.customer.behaviour_training()
    return PreparedData(
        ds, CustomerFeatureTransformer(), y=ds.targets["activity_level"]
    )


def _customer_retention(b: BuilderSet) -> PreparedData:
    ds = b.customer.behaviour_training()
    return PreparedData(ds, CustomerFeatureTransformer(), y=ds.targets["retained"])


def _transaction_success(b: BuilderSet) -> PreparedData:
    ds = b.transaction.success_training()
    return PreparedData(ds, TransactionFeatureTransformer(), y=ds.targets["success"])


def _merchant_autopay(b: BuilderSet) -> PreparedData:
    ds = b.merchant.autopay_training()
    return PreparedData(ds, MerchantFeatureTransformer(), y=ds.targets["adopted"])


def _customer_autopay(b: BuilderSet) -> PreparedData:
    ds = b.customer.autopay_training()
    return PreparedData(ds, CustomerFeatureTransformer(), y=ds.targets["adopted"])


def _merchant_segments(b: BuilderSet) -> PreparedData:
    ds = b.merchant.segmentation_training()
    return PreparedData(
        ds, MerchantFeatureTransformer(),
        segment_labels=config.MERCHANT_SEGMENTS,
        order_column="window_growth_pct",
    )


def _customer_segments(b: BuilderSet) -> PreparedData:
    ds = b.customer.segmentation_training(cap=config.CUSTOMER_SEGMENT_LIMIT)
    return PreparedData(
        ds, CustomerFeatureTransformer(),
        segment_labels=config.CUSTOMER_SEGMENTS,
        order_column="total_count",
    )


def _anomaly(b: BuilderSet) -> PreparedData:
    ds = b.timeseries.anomaly_training()
    return PreparedData(ds, DailySeriesFeatureTransformer())


#: The full trainer catalog, in training order.
TRAINER_SPECS: list[TrainerSpec] = [
    TrainerSpec(
        "merchant_growth_regressor", "regression",
        "Predicts next-period merchant transaction growth (%) from scale, "
        "behaviour, trend, and category features.",
        _merchant_growth_reg, ["merchant", "growth", "forecast"],
    ),
    TrainerSpec(
        "merchant_growth_classifier", "classification",
        "Classifies merchants into growth categories (Declining / Stable / "
        "Growing / High Growth) for the next period.",
        _merchant_growth_clf, ["merchant", "growth"],
    ),
    TrainerSpec(
        "customer_expected_usage", "regression",
        "Predicts a customer's next-period transaction count from H1 "
        "behaviour, momentum, and engagement features.",
        _customer_usage, ["customer", "behaviour", "forecast"],
    ),
    TrainerSpec(
        "customer_activity_level", "classification",
        "Classifies customers into next-period activity levels (Dormant / "
        "Occasional / Regular / Power).",
        _customer_activity, ["customer", "behaviour"],
    ),
    TrainerSpec(
        "customer_retention", "classification",
        "Predicts the probability a customer remains active next period.",
        _customer_retention, ["customer", "retention"],
    ),
    TrainerSpec(
        "transaction_success", "classification",
        "Predicts per-transaction success probability from amount, parties, "
        "category, and time-of-day features (outcome fields excluded).",
        _transaction_success, ["transaction", "reliability"],
    ),
    TrainerSpec(
        "merchant_autopay", "classification",
        "Predicts merchant Autopay adoption probability — the merchant "
        "opportunity score for mandate acquisition programs.",
        _merchant_autopay, ["merchant", "autopay", "opportunity"],
    ),
    TrainerSpec(
        "customer_autopay", "classification",
        "Predicts customer Autopay adoption probability — the customer "
        "opportunity score for mandate acquisition programs.",
        _customer_autopay, ["customer", "autopay", "opportunity"],
    ),
    TrainerSpec(
        "merchant_segmentation", "clustering",
        "K-means merchant segments mapped to business labels: Declining, "
        "Stable, Emerging, High Growth (ranked by window growth).",
        _merchant_segments, ["merchant", "segmentation"],
    ),
    TrainerSpec(
        "customer_segmentation", "clustering",
        "K-means customer segments mapped to business labels: Dormant, "
        "Occasional, Regular, Power (ranked by activity).",
        _customer_segments, ["customer", "segmentation"],
    ),
    TrainerSpec(
        "anomaly_detector", "anomaly",
        "Isolation-forest detector over daily volume, failure, and growth "
        "features; flags volume anomalies, failure spikes, growth anomalies.",
        _anomaly, ["timeseries", "anomaly"],
    ),
]
