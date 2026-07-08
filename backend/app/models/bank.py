"""Bank master ORM model.

Purpose:
    Reference data for every bank participating in the UPI ecosystem.

Business role:
    Banks appear on both legs of a transaction (debit/remitter side and
    credit/beneficiary side) and as PSP sponsor banks. Bank-level success
    rate and failure decomposition are core diagnostic dimensions of the
    platform.

Source CSV:
    scripts/dataset_generator/master/bank_master.csv (frozen — 30 rows).

Primary key:
    ``bank_id`` — natural key issued by the dataset generator (BANK001...).

Typical usage:
    Joined (in later phases) against the transaction fact's bank name
    columns to enrich analytics with bank type and short-code attributes.
"""

from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class Bank(Base):
    """A UPI member bank as defined in the frozen bank master."""

    __tablename__ = "bank_master"

    # ------------------------------------------------------------------
    # PRIMARY KEY
    # ------------------------------------------------------------------
    # Natural key from the frozen master (BANK001, BANK002, ...).
    bank_id: Mapped[str] = mapped_column(String(10), primary_key=True)

    # ------------------------------------------------------------------
    # BANK IDENTITY
    # ------------------------------------------------------------------
    # Full display name — matches the denormalized bank name values carried
    # on the transaction fact (payerbank / payeebank).
    bank_name: Mapped[str] = mapped_column(String(50), nullable=False)

    # Exchange short code (BARB, BKID, ...) used in operational reporting.
    bank_short_name: Mapped[str] = mapped_column(String(10), nullable=False)

    # ------------------------------------------------------------------
    # CLASSIFICATION
    # ------------------------------------------------------------------
    # Ownership classification (PUBLIC / PRIVATE) — a standard segmentation
    # axis for bank benchmarking analytics.
    bank_type: Mapped[str] = mapped_column(String(10), nullable=False)

    # IFSC prefix identifying the bank in account-routing contexts.
    ifsc_prefix: Mapped[str] = mapped_column(String(10), nullable=False)

    # ------------------------------------------------------------------
    # STATUS
    # ------------------------------------------------------------------
    # Active membership flag — dataset encodes 'Y'/'N' as a single
    # character, stored with dataset fidelity (no boolean conversion here).
    active_flag: Mapped[str] = mapped_column(String(1), nullable=False)

    def __repr__(self) -> str:
        return (
            f"<Bank(bank_id={self.bank_id!r}, "
            f"name={self.bank_name!r}, "
            f"type={self.bank_type!r})>"
        )
