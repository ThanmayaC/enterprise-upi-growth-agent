"""Reusable pandas helpers shared across feature transformers.

Purpose:
    One implementation of the small, repetitive frame operations every
    transformer needs (safe division, decimal coercion, column alignment),
    so no preprocessing logic is duplicated across modules.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Iterable

import numpy as np
import pandas as pd


def to_float(series: pd.Series) -> pd.Series:
    """Coerce a column of ``Decimal``/``None``/numbers to float, NaN-safe.

    The Service layer returns money as ``Decimal``; models need floats.
    """

    return series.map(
        lambda v: float(v) if isinstance(v, (Decimal, int, float)) else np.nan
    ).astype(float)


def safe_divide(
    numerator: "pd.Series | np.ndarray",
    denominator: "pd.Series | np.ndarray",
) -> np.ndarray:
    """Element-wise division guarded against divide-by-zero (→ 0.0).

    Accepts Series or arrays (so calls can be nested) and always returns a
    float ndarray, which pandas assigns positionally to frame columns.
    """

    num = np.asarray(numerator, dtype=float)
    den = np.asarray(denominator, dtype=float)
    return np.divide(num, den, out=np.zeros_like(num), where=den > 0)


def align_columns(frame: pd.DataFrame, columns: Iterable[str]) -> pd.DataFrame:
    """Return ``frame`` with exactly ``columns`` (missing filled 0, order fixed).

    Used at inference time so a single-row feature frame always matches the
    exact column set the model was trained on — the classic one-hot
    train/serve skew guard.
    """

    cols = list(columns)
    out = frame.reindex(columns=cols, fill_value=0)
    return out[cols]


def clip_outliers(series: pd.Series, lower: float = 0.01, upper: float = 0.99) -> pd.Series:
    """Winsorize a numeric series to its [lower, upper] quantiles."""

    s = series.astype(float)
    lo, hi = s.quantile(lower), s.quantile(upper)
    return s.clip(lo, hi)
