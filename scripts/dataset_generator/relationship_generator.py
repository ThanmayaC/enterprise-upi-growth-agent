"""
relationship_generator.py

Owns cross-row referential state that must stay consistent across an
entire transaction lifecycle and across the whole batch:
    - unique txnid pool
    - unique UMN pool
    - per-UMN payerseqnum counters (never skip, never decrease)
    - mandate metadata (validity window, recurrence pattern, operation)

transaction_generator.py delegates all "give me a fresh, valid X"
requests here so uniqueness/consistency rules are enforced in one place.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from random import Random
from typing import Dict, Optional

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
    mandateoperation: str
    validitystart: date
    validityend: date
    revokable: str
    next_seqnum: int = field(default=1)

    def take_seqnum(self) -> int:
        """Return the next payerseqnum for this UMN and advance the counter."""
        value = self.next_seqnum
        self.next_seqnum += 1
        return value


class RelationshipManager:
    """Central authority for txnid/UMN uniqueness and mandate state tracking."""

    def __init__(self, rng: Random) -> None:
        self.rng = rng
        self._used_txnids: set[str] = set()
        self._used_umns: set[str] = set()
        self._mandates: Dict[str, MandateContext] = {}

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

    def new_umn(
        self,
        customer: CustomerRecord,
        merchant: MerchantRecord,
        purposecode: str,
        initiationmode: str,
        recurrencepattern: str,
        mandateoperation: str,
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
            mandateoperation=mandateoperation,
            validitystart=validitystart,
            validityend=validityend,
            revokable=revokable,
        )
        self._mandates[umn] = ctx
        return ctx

    def get_mandate(self, umn: str) -> Optional[MandateContext]:
        """Look up an existing mandate context by UMN."""
        return self._mandates.get(umn)

    def active_mandates(self) -> list[MandateContext]:
        """Return all mandates created so far in this batch."""
        return list(self._mandates.values())

    def txnid_count(self) -> int:
        return len(self._used_txnids)

    def umn_count(self) -> int:
        return len(self._used_umns)
