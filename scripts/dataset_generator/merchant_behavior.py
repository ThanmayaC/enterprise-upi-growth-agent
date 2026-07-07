"""
merchant_behavior.py

Derives a behavioural archetype for each merchant from its existing MCC
(merchant_generator.py is not modified). This determines which business
events a merchant realistically drives — e.g. an OTT/SaaS merchant is
AUTOPAY_HEAVY (mostly AutoPay executions), a utility is BBPS_AUTOPAY, an
e-commerce/food-delivery merchant is MERCHANT_HEAVY (mostly one-off
merchant payments).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

import constants
from merchant_generator import MerchantRecord


@dataclass(frozen=True)
class MerchantBehaviorProfile:
    """Event-mix weighting for one merchant behaviour archetype."""

    archetype: str
    autopay_share: float       # probability this merchant's recurring txns are AutoPay
    bbps_share: float          # probability routed via BBPS rather than plain merchant payment
    oneoff_share: float        # probability of one-off (non-recurring) merchant payment
    high_value: bool           # whether amounts should skew to the high end of its MCC profile
    seasonal: bool             # whether volume should spike in specific months (fees/renewals)


BEHAVIOR_PROFILES: Dict[str, MerchantBehaviorProfile] = {
    "AUTOPAY_HEAVY": MerchantBehaviorProfile(
        archetype="AUTOPAY_HEAVY", autopay_share=0.85, bbps_share=0.0,
        oneoff_share=0.15, high_value=False, seasonal=False,
    ),
    "BBPS_AUTOPAY": MerchantBehaviorProfile(
        archetype="BBPS_AUTOPAY", autopay_share=0.45, bbps_share=0.45,
        oneoff_share=0.10, high_value=False, seasonal=False,
    ),
    "RECHARGE_AUTOPAY": MerchantBehaviorProfile(
        archetype="RECHARGE_AUTOPAY", autopay_share=0.40, bbps_share=0.30,
        oneoff_share=0.30, high_value=False, seasonal=False,
    ),
    "LARGE_MONTHLY_AUTOPAY": MerchantBehaviorProfile(
        archetype="LARGE_MONTHLY_AUTOPAY", autopay_share=0.70, bbps_share=0.0,
        oneoff_share=0.30, high_value=True, seasonal=False,
    ),
    "SEASONAL_LARGE": MerchantBehaviorProfile(
        archetype="SEASONAL_LARGE", autopay_share=0.20, bbps_share=0.0,
        oneoff_share=0.80, high_value=True, seasonal=True,
    ),
    "HIGH_VALUE": MerchantBehaviorProfile(
        archetype="HIGH_VALUE", autopay_share=0.05, bbps_share=0.0,
        oneoff_share=0.95, high_value=True, seasonal=False,
    ),
    "MERCHANT_HEAVY": MerchantBehaviorProfile(
        archetype="MERCHANT_HEAVY", autopay_share=0.05, bbps_share=0.0,
        oneoff_share=0.95, high_value=False, seasonal=False,
    ),
}


class MerchantBehaviorSimulator:
    """Looks up the behaviour archetype/profile for any merchant."""

    def archetype_for(self, merchant: MerchantRecord) -> str:
        """Return the behaviour archetype name for a merchant, keyed by MCC."""
        return constants.MCC_BEHAVIOR_PROFILE.get(merchant.mcc, constants.DEFAULT_MERCHANT_BEHAVIOR)

    def profile_for(self, merchant: MerchantRecord) -> MerchantBehaviorProfile:
        """Return the full behaviour profile for a merchant."""
        return BEHAVIOR_PROFILES[self.archetype_for(merchant)]
