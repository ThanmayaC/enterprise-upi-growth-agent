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
from typing import Dict, List, Optional, Sequence

import business_rules
from merchant_generator import MerchantRecord
from utils import derive_sub_seed

# Amount profiles now live in business_rules.py (the centralized Business
# Rule Engine, Task 1) so there is a single source of truth for "what
# should this merchant category typically charge" shared by every module
# that needs it. Kept as module-level aliases here for readability at
# call sites within this file.
MCC_AMOUNT_PROFILES = business_rules.AMOUNT_PROFILES
DEFAULT_AMOUNT_PROFILE = business_rules.DEFAULT_AMOUNT_PROFILE



class GrowthSimulator:
    """Encapsulates market-share and amount-distribution behaviour."""

    def __init__(self, rng: Random) -> None:
        self.rng = rng
        self._merchant_amount_personality_cache: Dict[str, float] = {}

    def merchant_amount_personality(self, merchant_id: str) -> float:
        """Return a stable (not per-call-random) amount multiplier in
        ~[0.65, 1.55] for a given merchant_id, so two merchants sharing an
        MCC (two restaurants, two grocery stores) still develop visibly
        distinct typical ticket sizes — one runs cheap, one runs
        expensive — instead of both sampling from an identical MCC-wide
        range. Deterministic from merchant_id, so it's stable across the
        whole run and across re-generation with the same seed."""
        if merchant_id not in self._merchant_amount_personality_cache:
            h = derive_sub_seed(0, merchant_id)
            factor = 0.65 + (h % 1000) / 1000.0 * 0.90
            self._merchant_amount_personality_cache[merchant_id] = factor
        return self._merchant_amount_personality_cache[merchant_id]

    def merchant_selection_weights(self, merchants: Sequence[MerchantRecord]) -> List[float]:
        """Return weights modeling genuine Pareto merchant concentration.

        Merchants are ranked (stable, deterministic order as provided) and
        weighted by a power-law: weight(rank) = 1 / rank**ALPHA. With
        ALPHA=1.16 the top ~20% of merchants absorb roughly 75-80% of
        total selection probability, matching real UPI merchant
        concentration (a handful of large chains/aggregators dominate
        volume while the long tail of small merchants gets few
        transactions each). Genre/type still nudge the base rank weight
        so LARGE/AGGREGATOR/ONLINE merchants land disproportionately in
        the high-weight ranks.
        """
        alpha = 1.16
        scored = []
        for idx, m in enumerate(merchants):
            genre_boost = {"LARGE": 3.0, "AGGREGATOR": 2.2, "SMALL": 1.0}.get(m.merchant_genre, 1.0)
            type_boost = 1.4 if m.merchant_type == "ONLINE" else (1.15 if m.merchant_type == "HYBRID" else 1.0)
            scored.append((idx, genre_boost * type_boost))
        # Rank by boosted score descending; higher-boosted merchants get
        # lower (better) ranks and thus higher Pareto weight.
        ranked = sorted(scored, key=lambda t: t[1], reverse=True)
        rank_weight = {orig_idx: 1.0 / ((rank + 1) ** alpha) for rank, (orig_idx, _) in enumerate(ranked)}
        return [rank_weight[i] * scored[i][1] for i in range(len(merchants))]

    def entity_market_share_weights(self, count: int) -> List[float]:
        """Return descending weights simulating bank/PSP market share.

        The first entities in the ordered list are treated as
        higher-market-share incumbents.
        """
        return [max(1.0, count - i) ** 1.4 for i in range(count)]

    def sample_amount(self, mcc: str, ticket_multiplier: float = 1.0, merchant_id: Optional[str] = None) -> float:
        """Sample a realistic transaction amount for a given MCC.

        ticket_multiplier scales the sampled amount (e.g. by customer
        persona or merchant high-value archetype) without altering the
        underlying MCC distribution shape. If merchant_id is given, the
        merchant's own stable amount personality is folded in too, so two
        merchants sharing an MCC still land at recognizably different
        typical ticket sizes.
        """
        low, mode, high = MCC_AMOUNT_PROFILES.get(mcc, DEFAULT_AMOUNT_PROFILE)
        personality = self.merchant_amount_personality(merchant_id) if merchant_id else 1.0
        amount = self.rng.triangular(low, high, mode) * ticket_multiplier * personality
        return round(amount, 2)

    def sample_p2p_amount(self, ticket_multiplier: float = 1.0) -> float:
        """Sample a realistic P2P (person-to-person) transaction amount."""
        return round(self.rng.triangular(20, 20000, 500) * ticket_multiplier, 2)
