"""Time, seasonality, trend, and failure features.

Two reusable pieces live here:

    - :func:`timestamp_features` — row-level calendar signals for any frame
      with a timestamp column (shared by the transaction transformer).
    - :class:`DailySeriesFeatureTransformer` — day-grain features for the
      anomaly detector, built from the Analytics daily trend series (volume,
      amount, failure counts): rolling baselines, deviations, day-over-day
      growth, and weekday seasonality.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from app.ml.feature_engineering.base import BaseFeatureTransformer
from app.ml.utils.frames import safe_divide, to_float

#: Rolling window (days) for the local baseline used in deviations.
ROLLING_WINDOW = 7


def timestamp_features(timestamps: pd.Series) -> pd.DataFrame:
    """Row-level calendar features from a timestamp column.

    Returns hour, day-of-week, weekend flag, month, and month-edge flags —
    the seasonality signals every transaction-grain model shares.
    """

    ts = pd.to_datetime(timestamps, errors="coerce")
    f = pd.DataFrame(index=timestamps.index)
    f["hour"] = ts.dt.hour.fillna(0).astype(float)
    f["day_of_week"] = ts.dt.dayofweek.fillna(0).astype(float)
    f["is_weekend"] = (ts.dt.dayofweek >= 5).astype(float)
    f["month"] = ts.dt.month.fillna(0).astype(float)
    f["is_month_start"] = (ts.dt.day <= 3).astype(float)   # salary-cycle window
    f["is_month_end"] = (ts.dt.day >= 28).astype(float)    # bill/mandate window
    f["is_evening_peak"] = ts.dt.hour.between(18, 22).astype(float)
    return f


class DailySeriesFeatureTransformer(BaseFeatureTransformer):
    """Day-grain trend/seasonality/failure features for anomaly detection.

    Input frame columns (from the dataset builder): ``period`` (date),
    ``transaction_count``, ``total_amount``, ``failure_count``.
    """

    def _build(self, frame: pd.DataFrame) -> pd.DataFrame:
        f = pd.DataFrame(index=frame.index)
        count = to_float(frame["transaction_count"])
        amount = to_float(frame["total_amount"])
        failures = to_float(frame["failure_count"])
        period = pd.to_datetime(frame["period"], errors="coerce")

        # --- Levels --------------------------------------------------
        f["transaction_count"] = count
        f["log_amount"] = np.log1p(amount)
        f["failure_count"] = failures
        f["failure_rate_pct"] = 100.0 * safe_divide(failures, count)

        # --- Trend: rolling baseline and deviation from it -------------
        roll_count = count.rolling(ROLLING_WINDOW, min_periods=1).mean()
        roll_fail = failures.rolling(ROLLING_WINDOW, min_periods=1).mean()
        f["count_vs_baseline"] = safe_divide(count, roll_count)
        f["failure_vs_baseline"] = safe_divide(failures, roll_fail)

        # --- Growth: day-over-day movement ------------------------------
        prev = count.shift(1)
        f["dod_growth_pct"] = (100.0 * safe_divide(count - prev, prev))
        f["dod_growth_pct"] = f["dod_growth_pct"].fillna(0.0)

        # --- Weekday seasonality -----------------------------------------
        f["day_of_week"] = period.dt.dayofweek.fillna(0).astype(float)
        f["is_weekend"] = (period.dt.dayofweek >= 5).astype(float)
        f["is_month_end"] = (period.dt.day >= 28).astype(float)
        return f
