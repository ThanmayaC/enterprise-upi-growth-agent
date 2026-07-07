"""
business_rules.py

Centralized, DETERMINISTIC Business Rule Engine.

Before this module existed, purpose codes, initiation modes, and amount
ranges were resolved independently (and partly randomly) at each call
site inside transaction_generator.py. This module is now the single
source of truth: given (transaction_type, mcc), it deterministically
derives every business-logic-driven value the generator needs:

    get_purpose_code(mcc, transaction_type)      -> official purpose code
    get_initiation_mode(transaction_type, mcc)    -> official initiation mode
    get_amount_profile(mcc)                       -> (low, mode, high) INR
    get_amount_range(mcc)                          -> (low, high) INR
    is_autopay_eligible(mcc)                       -> bool
    get_refund_probability(mcc)                    -> float 0..1
    get_retry_probability(transaction_type, mcc)    -> float 0..1
    get_default_success_rate(transaction_type)      -> float 0..1

No randomness lives here. Every purpose code and initiation mode
returned comes only from the official masters (constants.PURPOSE_CODES /
constants.INITIATION_MODES) — this module never invents a code, it only
picks *which* official code deterministically applies.
"""

from __future__ import annotations

from typing import Optional

import constants

# ---------------------------------------------------------------------------
# Amount profiles: (low, mode, high) INR per MCC. This is the single
# source of truth for transaction amount ranges — growth_simulator.py
# consumes this instead of keeping its own separate table.
# ---------------------------------------------------------------------------
AMOUNT_PROFILES: dict[str, tuple[float, float, float]] = {
    "5411": (50, 400, 3000),        # Grocery
    "5812": (150, 450, 1200),       # Restaurants / food delivery
    "5813": (100, 500, 3000),       # Bars
    "5912": (50, 300, 2000),        # Pharmacy
    "5311": (200, 1200, 15000),     # Department stores
    "5732": (500, 5000, 80000),     # Electronics
    "4121": (50, 200, 1500),        # Taxi
    "4111": (10, 30, 100),          # Local transit
    "4899": (150, 400, 2000),       # Cable/DTH
    "4814": (100, 350, 2000),       # Telecom
    "4900": (200, 1500, 8000),      # Utilities / electricity
    "6300": (500, 8000, 60000),     # Insurance
    "8011": (200, 800, 5000),       # Doctors
    "8062": (1000, 15000, 100000),  # Hospitals — large ticket, rare
    "8220": (5000, 50000, 500000),  # Colleges
    "8211": (1000, 20000, 200000),  # Schools
    "5964": (100, 1200, 25000),     # E-commerce
    "5999": (50, 600, 10000),       # Misc retail
    "7011": (1000, 6000, 60000),    # Hotels
    "4511": (1500, 8000, 60000),    # Airlines
    "5541": (100, 800, 4000),       # Fuel
    "6011": (500, 2000, 10000),     # ATM
    "6051": (500, 10000, 200000),   # Investments
    "7372": (99, 499, 5000),        # SaaS
    "7841": (99, 299, 1500),        # OTT
    "5691": (300, 1500, 15000),     # Apparel
    "5261": (100, 500, 5000),       # Nursery/garden
    "8398": (50, 500, 20000),       # Charity
    "6513": (5000, 25000, 100000),  # Rent
    "4131": (20, 60, 300),          # Bus
}
DEFAULT_AMOUNT_PROFILE: tuple[float, float, float] = (50, 500, 5000)


def get_amount_profile(mcc: Optional[str]) -> tuple[float, float, float]:
    """Return the (low, mode, high) triangular-distribution profile for
    an MCC, falling back to a generic default for unmapped/None MCCs."""
    if mcc is None:
        return DEFAULT_AMOUNT_PROFILE
    return AMOUNT_PROFILES.get(mcc, DEFAULT_AMOUNT_PROFILE)


def get_amount_range(mcc: Optional[str]) -> tuple[float, float]:
    """Return just the (low, high) bounds for an MCC."""
    low, _mode, high = get_amount_profile(mcc)
    return (low, high)


# ---------------------------------------------------------------------------
# Purpose code resolution — deterministic, sourced only from
# constants.MCC_TO_PURPOSE_CODES / constants.RECURRING_PURPOSE_CODES
# (both drawn from the official Purpose Code Master). Where the master
# lists multiple MCC-compatible codes, the FIRST is the fixed business-
# rule choice; there is no random pick among them anymore.
# ---------------------------------------------------------------------------
_RECURRING_TRANSACTION_TYPES: frozenset[str] = frozenset({
    "MANDATE_REGISTRATION", "MANDATE_UPDATE", "AUTOPAY_EXECUTION", "AUTOPAY_RETRY",
})


def get_purpose_code(mcc: Optional[str], transaction_type: str) -> str:
    """Deterministically resolve the official purpose code for a given
    (transaction_type, mcc) pair. Never random."""
    if transaction_type == "BBPS_PAYMENT":
        return "10"  # Purpose Master code 10 == BBPS
    if transaction_type == "INTERNATIONAL_PAYMENT":
        return "11"  # Purpose Master code 11 == Global UPI
    if transaction_type in _RECURRING_TRANSACTION_TYPES:
        candidates = [
            c for c in constants.MCC_TO_PURPOSE_CODES.get(mcc, ("14",))
            if c in constants.RECURRING_PURPOSE_CODES
        ] or list(constants.RECURRING_PURPOSE_CODES)
        return candidates[0]
    if mcc is None:
        return "00"  # P2P / no merchant category
    return constants.MCC_TO_PURPOSE_CODES.get(mcc, ("00",))[0]


# ---------------------------------------------------------------------------
# Initiation mode resolution — deterministic, sourced only from
# constants.INITIATION_MODES (official Initiation Mode Master).
# Primarily keyed by transaction_type; a small MCC override table adds
# category-specific nuance (e.g. ATM withdrawals) without introducing
# randomness.
# ---------------------------------------------------------------------------
_INITIATION_MODE_BY_TRANSACTION_TYPE: dict[str, str] = {
    "MANDATE_REGISTRATION": "11",     # UPI-Mandate
    "MANDATE_UPDATE": "11",
    "AUTOPAY_EXECUTION": "11",
    "AUTOPAY_RETRY": "11",
    "BBPS_PAYMENT": "14",             # Bill Payment
    "QR_PAYMENT": "15",               # Dynamic QR Code
    "INTERNATIONAL_PAYMENT": "49",    # Global Acceptance Secure Intent
    "COLLECT_PAYMENT": "05",          # Secure Intent (payee-initiated collect)
    "BALANCE_CHECK": "10",            # SDK-style account-info check
}
_INITIATION_MODE_MCC_OVERRIDES: dict[str, str] = {
    "6011": "18",  # ATM withdrawals -> Dynamic ATM
}
_DEFAULT_INITIATION_MODE = "04"  # Intent — default for P2P/MERCHANT_PAYMENT


def get_initiation_mode(transaction_type: str, mcc: Optional[str] = None) -> str:
    """Deterministically resolve the official initiation mode for a
    transaction. Never random."""
    if mcc is not None and mcc in _INITIATION_MODE_MCC_OVERRIDES:
        return _INITIATION_MODE_MCC_OVERRIDES[mcc]
    return _INITIATION_MODE_BY_TRANSACTION_TYPE.get(transaction_type, _DEFAULT_INITIATION_MODE)


# ---------------------------------------------------------------------------
# AutoPay eligibility — sourced from the official MCC Master's own
# "autopay_possible" flag (constants.MCC_LIST), not re-invented here.
# ---------------------------------------------------------------------------
_AUTOPAY_ELIGIBLE_MCCS: frozenset[str] = frozenset(
    row["mcc"] for row in constants.MCC_LIST if row["autopay_possible"] == "Y"
)


def is_autopay_eligible(mcc: Optional[str]) -> bool:
    """Whether a merchant category is eligible for AutoPay/mandate
    transactions, per the official MCC Master."""
    return mcc is not None and mcc in _AUTOPAY_ELIGIBLE_MCCS


# ---------------------------------------------------------------------------
# Refund probability — merchant-category-dependent. E-commerce/retail
# merchants (Amazon-like) refund noticeably more than restaurants or
# utility billers, matching real-world return/cancellation patterns.
# ---------------------------------------------------------------------------
_REFUND_PROBABILITY_BY_MCC: dict[str, float] = {
    "5964": 0.06,   # E-commerce — highest: returns/cancellations
    "5311": 0.04,   # Department stores
    "5732": 0.05,   # Electronics — high-value returns
    "5691": 0.05,   # Apparel — size/fit returns
    "5999": 0.03,   # Misc retail
    "7011": 0.02,   # Hotels — occasional booking cancellations
    "4511": 0.02,   # Airlines — occasional cancellations
    "5812": 0.005,  # Restaurants — rarely refunded
    "5813": 0.005,  # Bars
    "4121": 0.01,   # Taxi — occasional fare disputes
}
_DEFAULT_REFUND_PROBABILITY = 0.01


def get_refund_probability(mcc: Optional[str]) -> float:
    """Return the probability that a given merchant category's payment
    is eligible to generate a refund."""
    if mcc is None:
        return 0.0
    return _REFUND_PROBABILITY_BY_MCC.get(mcc, _DEFAULT_REFUND_PROBABILITY)


# ---------------------------------------------------------------------------
# Retry probability — how likely a *retryable* failure is actually
# retried, by transaction type. AutoPay/BBPS (billers actively chase
# failed collections) retry far more aggressively than a casual P2P
# transfer, which a person rarely bothers retrying immediately.
# ---------------------------------------------------------------------------
_RETRY_PROBABILITY_BY_TRANSACTION_TYPE: dict[str, float] = {
    "AUTOPAY_EXECUTION": 0.9,
    "AUTOPAY_RETRY": 0.9,
    "BBPS_PAYMENT": 0.65,
    "MANDATE_REGISTRATION": 0.5,
    "COLLECT_PAYMENT": 0.4,
    "MERCHANT_PAYMENT": 0.35,
    "QR_PAYMENT": 0.3,
    "P2P_PAYMENT": 0.25,
    "INTERNATIONAL_PAYMENT": 0.4,
}
_DEFAULT_RETRY_PROBABILITY = 0.3


def get_retry_probability(transaction_type: str, mcc: Optional[str] = None) -> float:
    """Return the probability that a retryable failure for this
    transaction type is actually retried (vs. abandoned)."""
    return _RETRY_PROBABILITY_BY_TRANSACTION_TYPE.get(transaction_type, _DEFAULT_RETRY_PROBABILITY)


# ---------------------------------------------------------------------------
# Default success rate — category baseline, blended by FailureSimulator
# with its existing contextual adjustments (amount, peak hour, PSP/bank
# reliability, merchant high-value archetype). Still resolves strictly to
# the two official Response Code Master outcomes (SUCCESS/FAILURE).
# ---------------------------------------------------------------------------
_DEFAULT_SUCCESS_RATE_BY_TRANSACTION_TYPE: dict[str, float] = {
    "P2P_PAYMENT": 0.97,
    "MERCHANT_PAYMENT": 0.95,
    "QR_PAYMENT": 0.94,
    "BBPS_PAYMENT": 0.97,
    "COLLECT_PAYMENT": 0.93,
    "AUTOPAY_EXECUTION": 0.93,
    "AUTOPAY_RETRY": 0.55,
    "MANDATE_REGISTRATION": 0.97,
    "MANDATE_UPDATE": 0.97,
    "MANDATE_PAUSE": 0.99,
    "MANDATE_RESUME": 0.98,
    "MANDATE_REVOKE": 0.99,
    "MERCHANT_REFUND": 0.99,
    "INTERNATIONAL_PAYMENT": 0.90,
    "BALANCE_CHECK": 0.99,
}


def get_default_success_rate(transaction_type: str, fallback: float = 0.94) -> float:
    """Return the category baseline success rate for a transaction type."""
    return _DEFAULT_SUCCESS_RATE_BY_TRANSACTION_TYPE.get(transaction_type, fallback)
