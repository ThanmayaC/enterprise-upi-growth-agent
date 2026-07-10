"""Merchant feature engineering.

Input frame (built by the merchant dataset builder from Analytics outputs):
one row per merchant with early-window (``p1_*``) and late-window (``p2_*``)
traffic, whole-window traffic (``total_*``, ``success_rate``), the
within-window growth columns, the merchant's ``mcc_code``, and — for autopay
work — the category's observed autopay intensity (``mcc_autopay_share``).

Feature families produced here (reused by *every* merchant model):
    - Scale        : volumes, amounts, platform share
    - Behaviour    : average ticket, success rate, failure rate
    - Growth/Trend : within-window growth %, momentum ratio, acceleration
    - Category     : one-hot MCC (top categories, rest pooled)
    - Autopay      : category autopay intensity × merchant scale/stability
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from app.ml.feature_engineering.base import BaseFeatureTransformer
from app.ml.utils.frames import safe_divide, to_float

#: Bounded MCC vocabulary (30 codes exist; keep all but stay explicit).
TOP_MCC = 30


class MerchantFeatureTransformer(BaseFeatureTransformer):
    """Scale, behaviour, growth, category, and autopay merchant features."""

    def _build(self, frame: pd.DataFrame) -> pd.DataFrame:
        f = pd.DataFrame(index=frame.index)

        # --- Scale ---------------------------------------------------
        total_txns = to_float(frame["total_transactions"])
        total_amount = to_float(frame["total_amount"])
        f["total_transactions"] = total_txns
        f["total_amount"] = total_amount
        f["log_transactions"] = np.log1p(total_txns)
        f["log_amount"] = np.log1p(total_amount)
        f["volume_share_pct"] = 100.0 * total_txns / max(total_txns.sum(), 1.0)

        # --- Behaviour -----------------------------------------------
        f["avg_ticket"] = safe_divide(total_amount, total_txns)
        success_rate = to_float(frame["success_rate"])
        f["success_rate"] = success_rate
        f["failure_rate"] = 100.0 - success_rate

        # --- Growth / trend (within the feature window: p1 → p2) ------
        p1 = to_float(frame["p1_transactions"])
        p2 = to_float(frame["p2_transactions"])
        f["p1_transactions"] = p1
        f["p2_transactions"] = p2
        f["window_growth_pct"] = 100.0 * safe_divide(p2 - p1, p1)
        f["momentum_ratio"] = safe_divide(p2, p1)
        # Late-window share of activity: >0.5 means accelerating.
        f["late_window_share"] = safe_divide(p2, p1 + p2)

        # --- Autopay opportunity context ------------------------------
        if "mcc_autopay_share" in frame.columns:
            share = to_float(frame["mcc_autopay_share"])
            f["mcc_autopay_share"] = share
            # Opportunity interaction: autopay-friendly category × scale.
            f["autopay_scale_interaction"] = share * np.log1p(total_txns)
            f["autopay_stability_interaction"] = share * (success_rate / 100.0)

        # --- Category ---------------------------------------------------
        cats = self.one_hot(frame, "mcc_code", prefix="mcc", top_n=TOP_MCC)
        return pd.concat([f, cats], axis=1)
