"""Reusable dataset builders — training, validation/testing, and inference.

Each builder turns :class:`MLDataProvider` frames into a model-ready
:class:`MLDataset`. The same builder serves every mode so preprocessing is
never duplicated:

    - ``train``     → features from the feature window (H1-2024), labels
                      from the label window (H2-2024): true out-of-window
                      supervision, no leakage. Train/test splitting happens
                      in the training pipeline.
    - ``inference`` → the identical feature recipe computed on the most
                      recent window (H2-2024), for single or batch
                      prediction of the *next* period.

Label policy (documented per builder):
    - Merchant growth   : H2-vs-H1 transaction growth %% (Analytics
                          ``get_merchant_growth``) + binned category.
    - Customer behaviour: H2 activity count (usage), activity-level bins,
                          retention = active in H2.
    - Transaction       : terminal ``status`` of the row itself.
    - Autopay adoption  : mandate/autopay activity observed in the autopay
                          label window (July–Aug 2024), matched per
                          merchant (via verified-name normalization) and
                          per customer (payer VPA).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

import numpy as np
import pandas as pd

from app.ml import config
from app.ml.datasets.data_provider import MLDataProvider
from app.ml.utils.frames import safe_divide, to_float

#: Transaction types that constitute mandate/autopay activity.
AUTOPAY_TYPES = (
    "AUTOPAY_EXECUTION",
    "AUTOPAY_RETRY",
    "MANDATE_REGISTRATION",
)

#: Dataset-verified suffix linking txn ``payee_name`` to ``merchant_name``.
_VERIFIED_SUFFIX = " Pvt Ltd"


@dataclass
class MLDataset:
    """A model-ready dataset: ids + raw feature frame + targets."""

    ids: pd.Series                       # entity identifiers, row-aligned
    frame: pd.DataFrame                  # raw feature frame (transformer input)
    targets: dict[str, pd.Series] = field(default_factory=dict)
    meta: dict[str, Any] = field(default_factory=dict)


def _bin_label(values: pd.Series, bins: list[tuple[float, str]]) -> pd.Series:
    """Map a numeric series to business category labels via ordered bins."""

    def assign(v: float) -> str:
        for upper, label in bins:
            if v <= upper:
                return label
        return bins[-1][1]

    return values.astype(float).map(assign)


def _normalize_payee_name(names: pd.Series) -> pd.Series:
    """Normalize txn ``payee_name`` (verified) to master ``merchant_name``."""

    return names.astype(str).str.removesuffix(_VERIFIED_SUFFIX).str.strip()


class MerchantDatasetBuilder:
    """Merchant frames for growth, autopay, and segmentation models."""

    def __init__(self, provider: MLDataProvider) -> None:
        self._provider = provider

    # ------------------------------------------------------------------
    # Feature frame (shared by every mode/model)
    # ------------------------------------------------------------------
    def feature_frame(
        self, start: date, mid: date, end: date,
        autopay_window: tuple[date, date], autopay_limit: int,
    ) -> pd.DataFrame:
        """One row per merchant: window traffic, sub-window split, autopay ctx."""

        total = self._provider.merchant_traffic(start, end)
        p1 = self._provider.merchant_traffic(start, mid)
        p2 = self._provider.merchant_traffic(mid + timedelta(days=1), end)

        frame = total[[
            "merchant_id", "merchant_name", "mcc_code",
            "total_transactions", "total_amount", "success_rate",
        ]].copy()
        frame = frame.merge(
            p1[["merchant_id", "total_transactions"]]
            .rename(columns={"total_transactions": "p1_transactions"}),
            on="merchant_id", how="left",
        ).merge(
            p2[["merchant_id", "total_transactions"]]
            .rename(columns={"total_transactions": "p2_transactions"}),
            on="merchant_id", how="left",
        )

        # Category autopay intensity observed in the (feature-side) window.
        sample = self._provider.transaction_sample(*autopay_window, limit=autopay_limit)
        mcc_share = _mcc_autopay_share(sample)
        frame["mcc_autopay_share"] = (
            frame["mcc_code"].map(mcc_share).fillna(0.0)
        )
        return frame

    def train_frame(self) -> pd.DataFrame:
        return self.feature_frame(
            config.FEATURE_START, config.FEATURE_MID, config.FEATURE_END,
            config.AUTOPAY_FEATURE_WINDOW, config.AUTOPAY_FEATURE_LIMIT,
        )

    def inference_frame(self) -> pd.DataFrame:
        return self.feature_frame(
            config.LABEL_START, config.LABEL_MID, config.LABEL_END,
            config.AUTOPAY_LABEL_WINDOW, config.AUTOPAY_LABEL_LIMIT,
        )

    # ------------------------------------------------------------------
    # Datasets
    # ------------------------------------------------------------------
    def growth_training(self) -> MLDataset:
        """Features H1, growth labels H2-vs-H1 (regression + category)."""

        frame = self.train_frame()
        growth = self._provider.merchant_growth(
            (config.LABEL_START, config.LABEL_END),
            (config.FEATURE_START, config.FEATURE_END),
        )[["merchant_id", "count_change_pct"]]
        merged = frame.merge(growth, on="merchant_id", how="inner")

        y_pct = to_float(merged["count_change_pct"]).clip(-100.0, 300.0)
        return MLDataset(
            ids=merged["merchant_id"],
            frame=merged,
            targets={
                "growth_pct": y_pct,
                "growth_category": _bin_label(y_pct, config.GROWTH_CATEGORY_BINS),
            },
        )

    def autopay_training(self) -> MLDataset:
        """Features H1; label = *above-median* mandate intensity in Jul–Aug.

        Nearly every merchant sees at least one mandate event in a two-month
        window, so a mere any-activity flag degenerates to a single class.
        The business question is *where autopay concentrates*, so the label
        is a median split on each merchant's mandate/autopay transaction
        count in the label window — balanced by construction.
        """

        frame = self.train_frame()
        sample = self._provider.transaction_sample(
            *config.AUTOPAY_LABEL_WINDOW, limit=config.AUTOPAY_LABEL_LIMIT
        )
        autopay = sample[sample["type"].isin(AUTOPAY_TYPES)]
        counts = autopay.groupby(
            _normalize_payee_name(autopay["payee_name"])
        ).size()
        merchant_counts = (
            frame["merchant_name"].astype(str).map(counts).fillna(0.0)
        )
        label = (merchant_counts > merchant_counts.median()).astype(int)
        return MLDataset(
            ids=frame["merchant_id"], frame=frame,
            targets={"adopted": pd.Series(label.to_numpy(), index=frame.index)},
        )

    def segmentation_training(self) -> MLDataset:
        """Unsupervised merchant frame (H1 features)."""

        frame = self.train_frame()
        return MLDataset(ids=frame["merchant_id"], frame=frame)

    def inference(self) -> MLDataset:
        """Batch-prediction frame on the latest window (H2-2024)."""

        frame = self.inference_frame()
        return MLDataset(ids=frame["merchant_id"], frame=frame)


class CustomerDatasetBuilder:
    """Customer frames for behaviour, autopay, and segmentation models."""

    def __init__(self, provider: MLDataProvider) -> None:
        self._provider = provider

    # ------------------------------------------------------------------
    # Feature frame (shared by every mode/model)
    # ------------------------------------------------------------------
    def feature_frame(
        self, start: date, mid: date, end: date,
        autopay_window: tuple[date, date], autopay_limit: int,
        limit: int,
    ) -> pd.DataFrame:
        """One row per active customer with p1/p2 activity + autopay usage."""

        p1 = self._provider.customer_traffic(start, mid, limit=limit)
        p2 = self._provider.customer_traffic(
            mid + timedelta(days=1), end, limit=limit
        )
        p1 = p1.rename(columns={"transaction_count": "p1_count",
                                "total_amount": "p1_amount"})
        p2 = p2.rename(columns={"transaction_count": "p2_count",
                                "total_amount": "p2_amount"})
        frame = p1[["customer_vpa", "p1_count", "p1_amount"]].merge(
            p2[["customer_vpa", "p2_count", "p2_amount"]],
            on="customer_vpa", how="outer",
        ).fillna(0.0)

        # Feature-window autopay usage per payer.
        sample = self._provider.transaction_sample(*autopay_window, limit=autopay_limit)
        autopay = sample[sample["type"].isin(AUTOPAY_TYPES)]
        usage = autopay.groupby("payer_vpa").size()
        frame["autopay_txns"] = frame["customer_vpa"].map(usage).fillna(0.0)
        return frame

    def train_frame(self) -> pd.DataFrame:
        return self.feature_frame(
            config.FEATURE_START, config.FEATURE_MID, config.FEATURE_END,
            config.AUTOPAY_FEATURE_WINDOW, config.AUTOPAY_FEATURE_LIMIT,
            limit=config.CUSTOMER_SAMPLE_LIMIT,
        )

    def inference_frame(self) -> pd.DataFrame:
        return self.feature_frame(
            config.LABEL_START, config.LABEL_MID, config.LABEL_END,
            config.AUTOPAY_LABEL_WINDOW, config.AUTOPAY_LABEL_LIMIT,
            limit=config.CUSTOMER_SAMPLE_LIMIT,
        )

    # ------------------------------------------------------------------
    # Datasets
    # ------------------------------------------------------------------
    def behaviour_training(self) -> MLDataset:
        """Features H1; labels = H2 usage, activity level, retention."""

        frame = self.train_frame()
        h2 = self._provider.customer_traffic(
            config.LABEL_START, config.LABEL_END,
            limit=config.CUSTOMER_LABEL_LIMIT,
        )
        h2_counts = h2.set_index("customer_vpa")["transaction_count"]
        usage = frame["customer_vpa"].map(h2_counts).fillna(0.0).astype(float)
        return MLDataset(
            ids=frame["customer_vpa"],
            frame=frame,
            targets={
                "expected_usage": usage,
                "activity_level": _bin_label(usage, config.ACTIVITY_LEVEL_BINS),
                "retained": (usage > 0).astype(int),
            },
        )

    def autopay_training(self) -> MLDataset:
        """Features H1; label = payer autopay activity in July–Aug 2024."""

        frame = self.train_frame()
        sample = self._provider.transaction_sample(
            *config.AUTOPAY_LABEL_WINDOW, limit=config.AUTOPAY_LABEL_LIMIT
        )
        autopay = sample[sample["type"].isin(AUTOPAY_TYPES)]
        adopters = set(autopay["payer_vpa"].astype(str))
        label = frame["customer_vpa"].astype(str).isin(adopters).astype(int)
        return MLDataset(
            ids=frame["customer_vpa"], frame=frame,
            targets={"adopted": pd.Series(label, index=frame.index)},
        )

    def segmentation_training(self, cap: int | None = None) -> MLDataset:
        """Unsupervised customer frame (H1 features, optionally capped)."""

        frame = self.train_frame()
        if cap is not None and len(frame) > cap:
            frame = frame.sample(n=cap, random_state=config.RANDOM_STATE)
            frame = frame.reset_index(drop=True)
        return MLDataset(ids=frame["customer_vpa"], frame=frame)

    def inference(self) -> MLDataset:
        frame = self.inference_frame()
        return MLDataset(ids=frame["customer_vpa"], frame=frame)


class TransactionDatasetBuilder:
    """Transaction-grain dataset for the success model."""

    #: Outcome-bearing columns — never allowed into the feature path.
    LEAK_COLUMNS = ("status", "error_code")

    def __init__(self, provider: MLDataProvider) -> None:
        self._provider = provider

    def success_training(self) -> MLDataset:
        """Sampled window rows; label = terminal SUCCESS/FAILURE outcome."""

        sample = self._provider.transaction_sample(
            config.TXN_SAMPLE_START, config.TXN_SAMPLE_END,
            limit=config.TXN_SAMPLE_LIMIT,
        )
        label = sample["status"].astype(str).str.upper().eq("SUCCESS").astype(int)
        frame = sample.drop(columns=list(self.LEAK_COLUMNS), errors="ignore")
        return MLDataset(
            ids=frame["transaction_id"], frame=frame,
            targets={"success": label},
        )

    def inference_frame(self, rows: list[dict[str, Any]]) -> pd.DataFrame:
        """Build a prediction frame from caller-supplied transaction dicts."""

        frame = pd.DataFrame(rows)
        return frame.drop(columns=list(self.LEAK_COLUMNS), errors="ignore")


class TimeSeriesDatasetBuilder:
    """Day-grain dataset for anomaly detection (volume/failure/growth)."""

    def __init__(self, provider: MLDataProvider) -> None:
        self._provider = provider

    def daily_frame(self, start: date | None = None,
                    end: date | None = None) -> pd.DataFrame:
        """Daily volume + failure series merged on the day."""

        volume = self._provider.daily_series(start=start, end=end)
        failures = self._provider.daily_series(status="FAILURE", start=start, end=end)
        fail_counts = failures.set_index("period")["transaction_count"]
        volume["failure_count"] = (
            volume["period"].map(fail_counts).fillna(0.0).astype(float)
        )
        return volume

    def anomaly_training(self) -> MLDataset:
        """Full-history daily frame (unsupervised)."""

        frame = self.daily_frame()
        return MLDataset(ids=frame["period"], frame=frame)


def _mcc_autopay_share(sample: pd.DataFrame) -> pd.Series:
    """Per-MCC share of mandate/autopay transactions in a sample window."""

    with_mcc = sample[sample["mcc_code"].notna() & (sample["mcc_code"] != "")]
    if with_mcc.empty:
        return pd.Series(dtype=float)
    is_autopay = with_mcc["type"].isin(AUTOPAY_TYPES)
    grouped = with_mcc.assign(autopay=is_autopay.astype(float)).groupby("mcc_code")
    return grouped["autopay"].mean()
