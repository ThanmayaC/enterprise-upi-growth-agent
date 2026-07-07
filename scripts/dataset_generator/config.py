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
    OUTPUT_FOLDER: Path = Path(__file__).resolve().parent
    MASTER_SUBDIR: str = "master"
    FACT_SUBDIR: str = "fact"

    # --- Date range ----------------------------------------------------------
    START_DATE: date = date(2024, 1, 1)
    END_DATE: date = date(2024, 12, 31)

    # --- Entity population sizes ---------------------------------------------
    NUMBER_OF_CUSTOMERS: int = 150_000
    NUMBER_OF_MERCHANTS: int = 500
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

    # --- Business-event top-level mix (percentages, must sum to ~100) ---------
    BUSINESS_EVENT_DISTRIBUTION: dict = field(default_factory=lambda: {
        "MERCHANT_PAYMENT": 40.0,
        "P2P_PAYMENT": 30.0,
        "QR_PAYMENT": 10.0,
        "COLLECT_PAYMENT": 5.0,
        "BBPS_PAYMENT": 5.0,
        "AUTOPAY_EXECUTION": 5.0,
        "MANDATE_REGISTRATION": 2.0,
        "MANDATE_UPDATE": 1.0,
        "MANDATE_PAUSE_RESUME_REVOKE": 1.0,
        "MERCHANT_REFUND": 1.0,
    })

    # --- Mandate execution timing: months between registration and first
    # execution, and gap (days) between subsequent PDN/execution cycles.
    MANDATE_FIRST_EXECUTION_MIN_DAYS: int = 25
    MANDATE_FIRST_EXECUTION_MAX_DAYS: int = 45
    MANDATE_CYCLE_GAP_MIN_DAYS: int = 25
    MANDATE_CYCLE_GAP_MAX_DAYS: int = 35
    PDN_LEAD_HOURS_MIN: int = 6
    PDN_LEAD_HOURS_MAX: int = 48

    # --- Retry behaviour for retryable failures --------------------------------
    MAX_RETRY_ATTEMPTS: int = 2
    RETRY_DELAY_MIN_MINUTES: int = 10
    RETRY_DELAY_MAX_MINUTES: int = 240
    RETRY_SUCCESS_PROBABILITY: float = 0.6

    # --- Mandate state-transition probabilities (per mandate, per month-check) -
    MANDATE_PAUSE_PROBABILITY: float = 0.03
    MANDATE_RESUME_PROBABILITY: float = 0.5
    MANDATE_REVOKE_PROBABILITY: float = 0.02
    MANDATE_UPDATE_PROBABILITY: float = 0.02

    # --- Refund behaviour --------------------------------------------------------
    REFUND_PROBABILITY_OF_MERCHANT_PAYMENT: float = 0.02
    REFUND_LAG_MIN_HOURS: int = 1
    REFUND_LAG_MAX_HOURS: int = 96

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
