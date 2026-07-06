"""
config.py

Central configuration for the synthetic UPI transaction dataset generator.
All tunable parameters live here. No other module should hardcode
generation-scale values (row counts, dates, entity counts, rates).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path


@dataclass(frozen=True)
class GeneratorConfig:
    """Holds every configurable parameter for a dataset generation run."""

    # --- Batch / scale control -------------------------------------------------
    ROWS_PER_BATCH: int = 50_000
    TOTAL_ROWS: int = 1_000_000
    RANDOM_SEED: int = 42

    # --- Output ------------------------------------------------------------
    OUTPUT_FOLDER: Path = Path(__file__).parent
    MASTER_SUBDIR: str = "master"
    FACT_SUBDIR: str = "fact"

    # --- Date range ----------------------------------------------------------
    START_DATE: date = date(2025, 1, 1)
    END_DATE: date = date(2026,5,31)

    # --- Entity population sizes ---------------------------------------------
    NUMBER_OF_CUSTOMERS: int = 200_000
    NUMBER_OF_MERCHANTS: int = 10_000
    NUMBER_OF_BANKS: int = 30
    NUMBER_OF_PSPS: int = 8

    # --- Outcome rates ---------------------------------------------------------
    SUCCESS_RATE: float = 0.94
    FAILURE_RATE: float = 0.06

    # --- Lifecycle mix: fraction of financial txns that are recurring/AutoPay --
    AUTOPAY_TXN_SHARE: float = 0.35
    # fraction of customers who are mandate-holders (subset of population)
    MANDATE_CUSTOMER_SHARE: float = 0.40
    # average number of recurring executions per active mandate over the window
    MAX_EXECUTIONS_PER_MANDATE: int = 12
    MIN_EXECUTIONS_PER_MANDATE: int = 1

    # --- API mix (approx percentages, must sum to ~100) -----------------------
    API_DISTRIBUTION: dict = field(default_factory=lambda: {
        "ReqPay": 22.0,
        "RespPay": 22.0,
        "ReqValCust": 10.0,
        "RespValCust": 10.0,
        "ReqMandate": 7.0,
        "RespMandate": 7.0,
        "ReqAuthMandate": 5.0,
        "RespAuthMandate": 5.0,
        "ReqMandateConfirmation": 4.0,
        "RespMandateConfirmation": 4.0,
        "ReqAuthValCust": 2.0,
        "RespAuthValCust": 2.0,
    })

    def master_path(self) -> Path:
        p = self.OUTPUT_FOLDER / self.MASTER_SUBDIR
        p.mkdir(parents=True, exist_ok=True)
        return p

    def fact_path(self) -> Path:
        p = self.OUTPUT_FOLDER / self.FACT_SUBDIR
        p.mkdir(parents=True, exist_ok=True)
        return p

    def number_of_batches(self) -> int:
        return max(1, -(-self.TOTAL_ROWS // self.ROWS_PER_BATCH))  # ceil div


DEFAULT_CONFIG = GeneratorConfig()
