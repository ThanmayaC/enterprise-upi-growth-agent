"""Transaction-level feature engineering.

Input frame: transaction summary DTO rows from the Service layer (``type``,
``category``, ``amount``, ``payer_bank``, ``payer_psp``, ``payee_bank``,
``mcc_code``, ``timestamp``). Produces the feature space for the transaction
success model.

Leakage policy: outcome-bearing columns (``status``, ``error_code``) are
*never* features — they are the label source and are dropped by the dataset
builder before this transformer runs.

Feature families:
    - Amount   : raw, log, and coarse magnitude buckets
    - Parties  : one-hot payer bank / payer PSP / payee bank (bounded vocab)
    - Type     : one-hot transaction type + financial/non-financial flag
    - Category : one-hot MCC (pooled tail)
    - Time     : hour / day-of-week / weekend / month-edge signals
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from app.ml.feature_engineering.base import BaseFeatureTransformer
from app.ml.feature_engineering.time_features import timestamp_features
from app.ml.utils.frames import to_float

#: Vocabulary caps keep the one-hot space bounded and stable.
TOP_BANKS = 30
TOP_PSPS = 8
TOP_MCC = 30
TOP_TYPES = 10


class TransactionFeatureTransformer(BaseFeatureTransformer):
    """Amount, party, type, category, and time features for one transaction."""

    def _build(self, frame: pd.DataFrame) -> pd.DataFrame:
        f = pd.DataFrame(index=frame.index)

        # --- Amount ------------------------------------------------------
        amount = to_float(frame["amount"]).fillna(0.0)
        f["amount"] = amount
        f["log_amount"] = np.log1p(amount.clip(lower=0))
        f["is_zero_amount"] = (amount <= 0).astype(float)  # mandate lifecycle rows
        f["amount_bucket_small"] = ((amount > 0) & (amount <= 500)).astype(float)
        f["amount_bucket_mid"] = ((amount > 500) & (amount <= 5_000)).astype(float)
        f["amount_bucket_large"] = (amount > 5_000).astype(float)

        # --- Type ----------------------------------------------------------
        f["is_financial"] = (
            frame["category"].astype(str).str.upper().eq("FINANCIAL").astype(float)
        )

        # --- Time ------------------------------------------------------------
        time_f = timestamp_features(frame["timestamp"])
        f = pd.concat([f, time_f], axis=1)

        # --- Categorical one-hots ---------------------------------------------
        parts = [
            f,
            self.one_hot(frame, "type", prefix="type", top_n=TOP_TYPES),
            self.one_hot(frame, "payer_bank", prefix="pbank", top_n=TOP_BANKS),
            self.one_hot(frame, "payee_bank", prefix="ybank", top_n=TOP_BANKS),
            self.one_hot(frame, "payer_psp", prefix="psp", top_n=TOP_PSPS),
            self.one_hot(frame, "mcc_code", prefix="mcc", top_n=TOP_MCC),
        ]
        return pd.concat(parts, axis=1)
