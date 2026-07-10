"""Base contract for all feature transformers.

Every transformer follows the scikit-learn ``fit`` / ``transform`` protocol
and, after fitting, exposes ``feature_names_`` — the exact, ordered feature
space the downstream model was trained on. At inference the same transformer
re-aligns new frames to that space (missing one-hot columns filled with 0),
eliminating train/serve skew by construction.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd

from app.ml.utils.frames import align_columns


class BaseFeatureTransformer(ABC):
    """Reusable ``fit``/``transform`` feature builder.

    Subclasses implement :meth:`_build`, which derives the raw feature frame
    from domain input; the base class owns vocabulary capture, NaN policy,
    column ordering, and train/serve alignment so that logic exists once.
    """

    def __init__(self) -> None:
        self.feature_names_: list[str] = []
        self._fitted = False

    # ------------------------------------------------------------------
    # Protocol
    # ------------------------------------------------------------------
    def fit(self, frame: pd.DataFrame) -> "BaseFeatureTransformer":
        """Learn feature vocabulary (one-hot categories, column order)."""

        built = self._finalize(self._build(frame))
        self.feature_names_ = list(built.columns)
        self._fitted = True
        return self

    def transform(self, frame: pd.DataFrame) -> pd.DataFrame:
        """Build features and align them to the fitted feature space."""

        if not self._fitted:
            raise RuntimeError(
                f"{type(self).__name__} must be fitted before transform()"
            )
        built = self._finalize(self._build(frame))
        return align_columns(built, self.feature_names_)

    def fit_transform(self, frame: pd.DataFrame) -> pd.DataFrame:
        """Fit on ``frame`` and return its features (training path)."""

        self.fit(frame)
        return align_columns(self._finalize(self._build(frame)), self.feature_names_)

    # ------------------------------------------------------------------
    # Subclass responsibility
    # ------------------------------------------------------------------
    @abstractmethod
    def _build(self, frame: pd.DataFrame) -> pd.DataFrame:
        """Derive the raw (pre-alignment) feature frame from domain input."""

    # ------------------------------------------------------------------
    # Shared mechanics
    # ------------------------------------------------------------------
    @staticmethod
    def _finalize(features: pd.DataFrame) -> pd.DataFrame:
        """Uniform NaN/dtype policy: numeric, NaN → 0, plain float columns."""

        out = features.copy()
        for col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")
        return out.fillna(0.0).astype(float)

    @staticmethod
    def one_hot(frame: pd.DataFrame, column: str, prefix: str,
                top_n: int | None = None) -> pd.DataFrame:
        """One-hot encode ``column`` (optionally only its ``top_n`` values).

        Rare values collapse into ``{prefix}_OTHER`` so the feature space
        stays bounded and stable across periods.
        """

        values = frame[column].fillna("UNKNOWN").astype(str)
        if top_n is not None:
            keep = values.value_counts().nlargest(top_n).index
            values = values.where(values.isin(keep), other="OTHER")
        dummies = pd.get_dummies(values, prefix=prefix, dtype=float)
        return dummies
