"""Customer feature engineering.

Input frame (built by the customer dataset builder from Analytics outputs):
one row per customer with early-window (``p1_*``) and late-window (``p2_*``)
activity plus whole-window totals. Optional autopay context columns carry the
customer's observed mandate/autopay usage in the feature window.

Feature families produced here (reused by *every* customer model):
    - Scale      : counts, amounts (log-scaled)
    - Behaviour  : average ticket, activity cadence (txns/week)
    - Growth     : early→late change, momentum, late-window share
    - Engagement : activity recency proxy, consistency across sub-windows
    - Autopay    : feature-window autopay usage flags
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from app.ml.feature_engineering.base import BaseFeatureTransformer
from app.ml.utils.frames import safe_divide, to_float

#: Days in each feature sub-window; used for cadence normalization.
WINDOW_DAYS = 91.0


class CustomerFeatureTransformer(BaseFeatureTransformer):
    """Scale, behaviour, growth, engagement, and autopay customer features."""

    def _build(self, frame: pd.DataFrame) -> pd.DataFrame:
        f = pd.DataFrame(index=frame.index)

        p1_count = to_float(frame["p1_count"])
        p2_count = to_float(frame["p2_count"])
        p1_amount = to_float(frame["p1_amount"])
        p2_amount = to_float(frame["p2_amount"])
        total_count = p1_count + p2_count
        total_amount = p1_amount + p2_amount

        # --- Scale -----------------------------------------------------
        f["total_count"] = total_count
        f["total_amount"] = total_amount
        f["log_count"] = np.log1p(total_count)
        f["log_amount"] = np.log1p(total_amount)

        # --- Behaviour ---------------------------------------------------
        f["avg_ticket"] = safe_divide(total_amount, total_count)
        f["txns_per_week"] = total_count / (2 * WINDOW_DAYS / 7.0)

        # --- Growth / momentum -------------------------------------------
        f["p1_count"] = p1_count
        f["p2_count"] = p2_count
        f["count_growth_pct"] = 100.0 * safe_divide(p2_count - p1_count, p1_count)
        f["momentum_ratio"] = safe_divide(p2_count, p1_count)
        f["late_window_share"] = safe_divide(p2_count, total_count)

        # --- Engagement ---------------------------------------------------
        # Active in both sub-windows → consistent user; late-only → new/rising.
        f["active_both_windows"] = ((p1_count > 0) & (p2_count > 0)).astype(float)
        f["active_late_only"] = ((p1_count == 0) & (p2_count > 0)).astype(float)
        f["ticket_shift"] = safe_divide(
            safe_divide(p2_amount, p2_count), safe_divide(p1_amount, p1_count)
        )

        # --- Autopay usage in the feature window ---------------------------
        if "autopay_txns" in frame.columns:
            autopay = to_float(frame["autopay_txns"])
            f["autopay_txns"] = autopay
            f["uses_autopay"] = (autopay > 0).astype(float)
            f["autopay_share"] = safe_divide(autopay, total_count)

        return f
