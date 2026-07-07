"""
relationship_generator.py

Owns all cross-row referential and stateful data that must remain
consistent across the whole batch:
    - unique txnid pool
    - unique UMN pool and per-UMN payerseqnum counters (never skip/decrease)
    - mandate lifecycle state machine (ACTIVE/PAUSED/REVOKED/EXPIRED/
      FAILED/UPDATED/SUSPENDED) with legal-transition enforcement
    - customer / merchant / payment / retry history, for behavioural
      continuity (e.g. "has this customer paid this merchant before")

transaction_generator.py delegates all "give me a fresh, valid X" and all
state-mutating requests here so uniqueness/consistency rules live in one
place.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime
from random import Random
from typing import Dict, List, Optional

import constants
from customer_generator import CustomerRecord
from merchant_generator import MerchantRecord
from utils import generate_custrefno, generate_txnid, generate_umn


@dataclass
class MandateContext:
    """Stateful record of one mandate's lifecycle for consistent reuse."""

    umn: str
    customer: CustomerRecord
    merchant: MerchantRecord
    purposecode: str
    initiationmode: str
    recurrencepattern: str
    validitystart: date
    validityend: date
    revokable: str
    state: str = "ACTIVE"
    next_seqnum: int = field(default=1)
    last_event_ts: Optional[datetime] = None
    next_due_date: Optional[date] = None
    total_executions: int = 0
    total_failures: int = 0
    consecutive_failures: int = 0

    def take_seqnum(self) -> int:
        """Return the next payerseqnum for this UMN and advance the counter."""
        value = self.next_seqnum
        self.next_seqnum += 1
        return value

    def is_executable(self) -> bool:
        return self.state in constants.EXECUTABLE_MANDATE_STATES

    def can_transition_to(self, new_state: str) -> bool:
        return new_state in constants.MANDATE_STATE_TRANSITIONS.get(self.state, ())

    def transition_to(self, new_state: str) -> bool:
        """Apply a state transition if legal; return whether it was applied."""
        if not self.can_transition_to(new_state):
            return False
        self.state = new_state
        return True


@dataclass
class CustomerPreferenceProfile:
    """Stable, once-assigned behavioural preferences for one customer,
    layered on top of persona (persona_simulator.py) and merchant
    archetype (merchant_behavior.py): a handful of favourite merchants
    this customer keeps returning to, the merchant categories (MCCs)
    those favourites belong to, a personal preferred hour-of-day, a
    personal preferred weekday or two (e.g. "always orders in on
    Fridays"), and a personal spend multiplier. This is what makes two
    customers with the same persona still look like distinct
    individuals."""

    favorite_merchant_ids: List[str]
    favorite_mccs: List[str]
    preferred_hour_center: int
    preferred_hour_spread: int
    preferred_weekdays: List[int]
    spend_multiplier: float


@dataclass
class RetryAttempt:
    """One retry attempt recorded against a prior failed transaction."""

    original_txnid: str
    attempt_number: int
    ts: datetime
    outcome_status: str


class RelationshipManager:
    """Central authority for uniqueness, mandate state, and history tracking."""

    def __init__(self, rng: Random) -> None:
        self.rng = rng
        self._used_txnids: set[str] = set()
        self._used_umns: set[str] = set()
        self._mandates: Dict[str, MandateContext] = {}

        # History tracking (Rule: RelationshipManager maintains history).
        self.customer_payment_history: Dict[str, List[str]] = defaultdict(list)  # customer_id -> txnids
        self.merchant_payment_history: Dict[str, List[str]] = defaultdict(list)  # merchant_id -> txnids
        self.customer_merchant_pairs_seen: set[tuple[str, str]] = set()
        self.retry_history: Dict[str, List[RetryAttempt]] = defaultdict(list)  # original_txnid -> attempts
        self.mandate_state_history: Dict[str, List[str]] = defaultdict(list)  # umn -> state sequence

        self._preferences: Dict[str, CustomerPreferenceProfile] = {}

    # ------------------------------------------------------------------
    # Identifier issuance
    # ------------------------------------------------------------------
    def new_txnid(self) -> str:
        """Return a globally unique transaction id."""
        while True:
            txnid = generate_txnid(self.rng)
            if txnid not in self._used_txnids:
                self._used_txnids.add(txnid)
                return txnid

    def new_custrefno(self) -> str:
        """Return a customer reference number (uniqueness not mandatory)."""
        return generate_custrefno(self.rng)

    # ------------------------------------------------------------------
    # Mandate lifecycle
    # ------------------------------------------------------------------
    def new_umn(
        self,
        customer: CustomerRecord,
        merchant: MerchantRecord,
        purposecode: str,
        initiationmode: str,
        recurrencepattern: str,
        validitystart: date,
        validityend: date,
        revokable: str,
    ) -> MandateContext:
        """Create and register a brand-new, globally unique mandate/UMN."""
        while True:
            umn = generate_umn(self.rng)
            if umn not in self._used_umns:
                self._used_umns.add(umn)
                break
        ctx = MandateContext(
            umn=umn,
            customer=customer,
            merchant=merchant,
            purposecode=purposecode,
            initiationmode=initiationmode,
            recurrencepattern=recurrencepattern,
            validitystart=validitystart,
            validityend=validityend,
            revokable=revokable,
        )
        self._mandates[umn] = ctx
        self.mandate_state_history[umn].append(ctx.state)
        return ctx

    def get_mandate(self, umn: str) -> Optional[MandateContext]:
        """Look up an existing mandate context by UMN."""
        return self._mandates.get(umn)

    def active_mandates(self) -> list[MandateContext]:
        """Return all mandates created so far in this batch."""
        return list(self._mandates.values())

    def executable_mandates(self) -> list[MandateContext]:
        """Return mandates currently eligible for PDN/execution."""
        return [m for m in self._mandates.values() if m.is_executable()]

    def apply_mandate_transition(self, ctx: MandateContext, new_state: str) -> bool:
        """Attempt a state transition and record it in history if applied."""
        applied = ctx.transition_to(new_state)
        if applied:
            self.mandate_state_history[ctx.umn].append(new_state)
        return applied

    # ------------------------------------------------------------------
    # History tracking
    # ------------------------------------------------------------------
    def record_payment(self, customer: CustomerRecord, merchant: Optional[MerchantRecord], txnid: str) -> None:
        """Record a payment event against customer/merchant history."""
        self.customer_payment_history[customer.customer_id].append(txnid)
        if merchant is not None:
            self.merchant_payment_history[merchant.merchant_id].append(txnid)
            self.customer_merchant_pairs_seen.add((customer.customer_id, merchant.merchant_id))

    def has_prior_relationship(self, customer: CustomerRecord, merchant: MerchantRecord) -> bool:
        """Whether this customer has paid this merchant before in this batch."""
        return (customer.customer_id, merchant.merchant_id) in self.customer_merchant_pairs_seen

    def record_retry(self, original_txnid: str, attempt_number: int, ts: datetime, outcome_status: str) -> None:
        """Record a retry attempt against an original failed transaction."""
        self.retry_history[original_txnid].append(
            RetryAttempt(original_txnid=original_txnid, attempt_number=attempt_number, ts=ts, outcome_status=outcome_status)
        )

    # ------------------------------------------------------------------
    # Counters
    # ------------------------------------------------------------------
    def txnid_count(self) -> int:
        return len(self._used_txnids)

    def umn_count(self) -> int:
        return len(self._used_umns)

    # ------------------------------------------------------------------
    # Customer preference profiles (favourite merchants, timing, spend)
    # ------------------------------------------------------------------
    def build_customer_preferences(self, customers: list, merchants: list, merchant_cum_weights: list, rng: Random) -> None:
        """Assign a stable per-customer preference profile once, up front.
        Favourite merchants are drawn from the same weighted pool used for
        one-off events, so favourites plausibly tilt toward popular,
        one-off-shaped merchants (Amazon, Swiggy) rather than AutoPay-only
        ones. This is what lets a customer "develop history" — Amazon,
        Swiggy, Amazon, recharge, Netflix — instead of transacting with a
        uniformly random merchant every single time.

        Takes precomputed cum_weights (not raw weights): at real-world
        customer counts, recomputing a cumulative-weight array from
        scratch for every single customer is a meaningful cost multiplied
        hundreds of thousands of times."""
        for customer in customers:
            n_favorites = rng.randint(3, 7)
            sampled = rng.choices(merchants, cum_weights=merchant_cum_weights, k=n_favorites)
            favorite_ids = list({m.merchant_id for m in sampled})
            favorite_mccs = list({m.mcc for m in sampled})
            n_preferred_days = rng.randint(1, 3)
            preferred_weekdays = rng.sample(range(7), k=n_preferred_days)
            self._preferences[customer.customer_id] = CustomerPreferenceProfile(
                favorite_merchant_ids=favorite_ids,
                favorite_mccs=favorite_mccs,
                preferred_hour_center=rng.randint(7, 22),
                preferred_hour_spread=rng.randint(1, 4),
                preferred_weekdays=preferred_weekdays,
                spend_multiplier=round(rng.uniform(0.75, 1.35), 3),
            )

    def preference_for(self, customer) -> Optional[CustomerPreferenceProfile]:
        """Return the assigned preference profile for a customer, if built."""
        return self._preferences.get(customer.customer_id)
