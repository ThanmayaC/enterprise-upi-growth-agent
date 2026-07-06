"""
growth_simulator.py

Provides realistic, non-uniform selection weights and amount
distributions: merchant concentration (a small share of merchants get
most volume), PSP/bank market share curves, and MCC-aware transaction
amount ranges. Used by transaction_generator.py to avoid a
"looks random" dataset.
"""

from __future__ import annotations

from random import Random
from typing import Dict, List, Sequence

from merchant_generator import MerchantRecord

# Amount distribution presets per MCC category flavor (min, mode, max) in INR,
# used to sample a triangular distribution that mimics realistic UPI ticket sizes.
MCC_AMOUNT_PROFILES: Dict[str, tuple[float, float, float]] = {
    "5411": (50, 400, 3000),      # Grocery
    "5812": (80, 350, 2500),      # Restaurants
    "5813": (100, 500, 3000),     # Bars
    "5912": (50, 300, 2000),      # Pharmacy
    "5311": (200, 1200, 15000),   # Department stores
    "5732": (500, 5000, 80000),   # Electronics
    "4121": (50, 200, 1500),      # Taxi
    "4111": (10, 30, 100),        # Transit
    "4899": (150, 400, 2000),     # Cable/DTH
    "4814": (100, 350, 2000),     # Telecom
    "4900": (200, 1500, 8000),    # Utilities
    "6300": (500, 8000, 60000),   # Insurance
    "8011": (200, 800, 5000),     # Doctors
    "8062": (500, 15000, 300000),  # Hospitals
    "8220": (5000, 50000, 500000),  # Colleges
    "8211": (1000, 20000, 200000),  # Schools
    "5964": (100, 1200, 25000),   # E-commerce
    "5999": (50, 600, 10000),     # Misc retail
    "7011": (1000, 6000, 60000),  # Hotels
    "4511": (1500, 8000, 60000),  # Airlines
    "5541": (100, 800, 4000),     # Fuel
    "6011": (500, 2000, 10000),   # ATM
    "6051": (500, 10000, 200000),  # Investments
    "7372": (99, 499, 5000),      # SaaS
    "7841": (99, 299, 1500),      # OTT
    "5691": (300, 1500, 15000),   # Apparel
    "5261": (100, 500, 5000),     # Nursery/garden
    "8398": (50, 500, 20000),     # Charity
    "6513": (5000, 25000, 100000),  # Rent
    "4131": (20, 60, 300),        # Bus
}
DEFAULT_AMOUNT_PROFILE: tuple[float, float, float] = (50, 500, 5000)


class GrowthSimulator:
    """Encapsulates market-share and amount-distribution behaviour."""

    def __init__(self, rng: Random) -> None:
        self.rng = rng

    def merchant_selection_weights(self, merchants: Sequence[MerchantRecord]) -> List[float]:
        """Return weights modeling merchant concentration (Pareto-like).

        A small subset of merchants (large genre / large onboarding chains)
        capture disproportionate transaction volume, matching real UPI
        merchant concentration patterns.
        """
        weights: List[float] = []
        for m in merchants:
            base = 1.0
            if m.merchant_genre == "LARGE":
                base *= 6.0
            elif m.merchant_genre == "AGGREGATOR":
                base *= 4.0
            if m.merchant_type == "ONLINE":
                base *= 1.5
            weights.append(base)
        return weights

    def entity_market_share_weights(self, count: int) -> List[float]:
        """Return descending weights simulating bank/PSP market share.

        The first entities in the ordered list are treated as
        higher-market-share incumbents.
        """
        return [max(1.0, count - i) ** 1.4 for i in range(count)]

    def sample_amount(self, mcc: str) -> float:
        """Sample a realistic transaction amount for a given MCC."""
        low, mode, high = MCC_AMOUNT_PROFILES.get(mcc, DEFAULT_AMOUNT_PROFILE)
        amount = self.rng.triangular(low, high, mode)
        return round(amount, 2)

    def sample_p2p_amount(self) -> float:
        """Sample a realistic P2P (person-to-person) transaction amount."""
        return round(self.rng.triangular(20, 20000, 500), 2)
