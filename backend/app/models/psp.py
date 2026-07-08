"""PSP (Payment Service Provider) master ORM model.

Purpose:
    Reference data for every PSP application in the UPI ecosystem
    (PhonePe, Google Pay, BHIM, ...).

Business role:
    PSPs are the consumer-facing applications through which transactions
    are initiated. PSP leaderboards, PSP-level failure heatmaps, and
    PSP growth trajectories are first-class analytics of the platform.

Source CSV:
    scripts/dataset_generator/master/psp_master.csv (frozen — 8 rows).

Primary key:
    ``psp_id`` — natural key issued by the dataset generator (PSP001...).

Typical usage:
    Joined (in later phases) against the transaction fact's PSP name and
    org-id columns to enrich analytics with handle and sponsor-bank data.
"""

from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class Psp(Base):
    """A UPI payment service provider as defined in the frozen PSP master."""

    __tablename__ = "psp_master"

    # ------------------------------------------------------------------
    # PRIMARY KEY
    # ------------------------------------------------------------------
    # Natural key from the frozen master (PSP001, PSP002, ...).
    psp_id: Mapped[str] = mapped_column(String(10), primary_key=True)

    # ------------------------------------------------------------------
    # PSP IDENTITY
    # ------------------------------------------------------------------
    # Consumer-facing application name — matches the denormalized PSP name
    # values carried on the transaction fact (payerpsp / initiatorpsp).
    psp_name: Mapped[str] = mapped_column(String(30), nullable=False)

    # Network organization id (column: orgid — ORG0001, ...) — the wire-level
    # identifier that the fact table carries as payerpsporgid/payeepsporgid.
    org_id: Mapped[str] = mapped_column("orgid", String(10), nullable=False)

    # VPA handle suffix operated by this PSP (YBL, OKAXIS, APL, ...) — the
    # '@handle' part of customer and merchant virtual payment addresses.
    handle: Mapped[str] = mapped_column(String(10), nullable=False)

    # ------------------------------------------------------------------
    # SPONSORSHIP
    # ------------------------------------------------------------------
    # Sponsor bank providing the PSP's UPI connectivity — needed to separate
    # issuer-bank failures from sponsor-bank failures in reliability work.
    sponsor_bank: Mapped[str] = mapped_column(String(50), nullable=False)

    # ------------------------------------------------------------------
    # STATUS
    # ------------------------------------------------------------------
    # Active participation flag — dataset encodes 'Y'/'N' as a single
    # character, stored with dataset fidelity (no boolean conversion here).
    active_flag: Mapped[str] = mapped_column(String(1), nullable=False)

    def __repr__(self) -> str:
        return (
            f"<Psp(psp_id={self.psp_id!r}, "
            f"name={self.psp_name!r}, "
            f"handle={self.handle!r})>"
        )
