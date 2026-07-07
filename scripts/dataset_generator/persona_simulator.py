"""
persona_simulator.py

Assigns a deterministic behavioural persona to each customer and exposes
persona-driven weighting used by transaction_generator.py. This is a
standalone layer on top of CustomerRecord (customer_generator.py is not
modified) so persona logic can evolve independently of identity data.

Personas: SALARY_EMPLOYEE, COLLEGE_STUDENT, BUSINESS_OWNER, RETIRED,
FAMILY, FREELANCER.
"""

from __future__ import annotations

from dataclasses import dataclass
from random import Random
from typing import Dict, List

import constants
from customer_generator import CustomerRecord


@dataclass(frozen=True)
class PersonaProfile:
    """Behavioural weighting for one customer persona."""

    persona: str
    # Relative preference multipliers across top-level business event families.
    merchant_payment_weight: float
    p2p_weight: float
    qr_weight: float
    bbps_weight: float
    autopay_affinity: float  # likelihood of holding/using a mandate
    avg_ticket_multiplier: float  # scales sampled amounts up/down
    salary_day_affinity: float  # extra activity clustering on salary days
    night_activity_multiplier: float  # OTT/late-night spend tendency


PERSONA_PROFILES: Dict[str, PersonaProfile] = {
    "SALARY_EMPLOYEE": PersonaProfile(
        persona="SALARY_EMPLOYEE", merchant_payment_weight=1.1, p2p_weight=0.9,
        qr_weight=1.0, bbps_weight=1.1, autopay_affinity=1.3,
        avg_ticket_multiplier=1.0, salary_day_affinity=1.6, night_activity_multiplier=1.0,
    ),
    "COLLEGE_STUDENT": PersonaProfile(
        persona="COLLEGE_STUDENT", merchant_payment_weight=1.3, p2p_weight=1.4,
        qr_weight=1.4, bbps_weight=0.4, autopay_affinity=0.6,
        avg_ticket_multiplier=0.5, salary_day_affinity=0.5, night_activity_multiplier=1.6,
    ),
    "BUSINESS_OWNER": PersonaProfile(
        persona="BUSINESS_OWNER", merchant_payment_weight=1.0, p2p_weight=0.7,
        qr_weight=0.9, bbps_weight=1.2, autopay_affinity=1.1,
        avg_ticket_multiplier=2.2, salary_day_affinity=0.7, night_activity_multiplier=0.7,
    ),
    "RETIRED": PersonaProfile(
        persona="RETIRED", merchant_payment_weight=0.7, p2p_weight=0.8,
        qr_weight=0.4, bbps_weight=1.4, autopay_affinity=1.4,
        avg_ticket_multiplier=1.1, salary_day_affinity=1.2, night_activity_multiplier=0.3,
    ),
    "FAMILY": PersonaProfile(
        persona="FAMILY", merchant_payment_weight=1.2, p2p_weight=0.9,
        qr_weight=0.9, bbps_weight=1.3, autopay_affinity=1.5,
        avg_ticket_multiplier=1.3, salary_day_affinity=1.4, night_activity_multiplier=0.8,
    ),
    "FREELANCER": PersonaProfile(
        persona="FREELANCER", merchant_payment_weight=1.0, p2p_weight=1.2,
        qr_weight=1.1, bbps_weight=0.9, autopay_affinity=0.9,
        avg_ticket_multiplier=0.9, salary_day_affinity=0.4, night_activity_multiplier=1.3,
    ),
}

# Population mix (percentages, config-independent — behavioural, not a
# tunable financial parameter, so kept alongside the profiles it describes).
PERSONA_POPULATION_WEIGHTS: Dict[str, float] = {
    "SALARY_EMPLOYEE": 35.0,
    "COLLEGE_STUDENT": 15.0,
    "BUSINESS_OWNER": 15.0,
    "RETIRED": 10.0,
    "FAMILY": 20.0,
    "FREELANCER": 5.0,
}

# Activity tiers (Task 5: "Heavy users, Dormant users, Power users,
# Business users") — an independent axis from persona. A power user and a
# dormant user can both be, say, SALARY_EMPLOYEE personas; this is what
# actually drives *how often* they show up in the generated stream,
# rather than every customer transacting with equal average frequency.
ACTIVITY_TIERS: tuple[str, ...] = ("DORMANT", "LOW", "REGULAR", "POWER")
ACTIVITY_TIER_POPULATION_WEIGHTS: Dict[str, float] = {
    "DORMANT": 10.0,
    "LOW": 25.0,
    "REGULAR": 50.0,
    "POWER": 15.0,
}
ACTIVITY_TIER_MULTIPLIERS: Dict[str, float] = {
    "DORMANT": 0.12,
    "LOW": 0.5,
    "REGULAR": 1.0,
    "POWER": 2.6,
}


class PersonaSimulator:
    """Assigns and looks up personas for the customer population."""

    def __init__(self, customers: List[CustomerRecord], rng: Random) -> None:
        self._by_customer_id: Dict[str, str] = {}
        self._activity_tier_by_customer_id: Dict[str, str] = {}
        personas = list(PERSONA_POPULATION_WEIGHTS.keys())
        weights = list(PERSONA_POPULATION_WEIGHTS.values())
        tiers = list(ACTIVITY_TIER_POPULATION_WEIGHTS.keys())
        tier_weights = list(ACTIVITY_TIER_POPULATION_WEIGHTS.values())
        for customer in customers:
            persona = rng.choices(personas, weights=weights, k=1)[0]
            self._by_customer_id[customer.customer_id] = persona
            self._activity_tier_by_customer_id[customer.customer_id] = rng.choices(
                tiers, weights=tier_weights, k=1
            )[0]

    def persona_for(self, customer: CustomerRecord) -> str:
        """Return the assigned persona name for a customer."""
        return self._by_customer_id.get(customer.customer_id, "SALARY_EMPLOYEE")

    def profile_for(self, customer: CustomerRecord) -> PersonaProfile:
        """Return the full behavioural profile for a customer."""
        return PERSONA_PROFILES[self.persona_for(customer)]

    def activity_tier_for(self, customer: CustomerRecord) -> str:
        """Return the assigned activity tier (DORMANT/LOW/REGULAR/POWER)."""
        return self._activity_tier_by_customer_id.get(customer.customer_id, "REGULAR")

    def activity_multiplier_for(self, customer: CustomerRecord) -> float:
        """Return the selection-frequency multiplier for this customer's
        activity tier — dormant customers appear rarely, power users
        appear far more often than an average customer."""
        return ACTIVITY_TIER_MULTIPLIERS[self.activity_tier_for(customer)]
