"""Merchant master ORM model.

Purpose:
    Reference data for every merchant accepting UPI payments in the
    frozen dataset.

Business role:
    Merchants are the payee side of P2M commerce. Merchant category (MCC)
    penetration, onboarding-channel analysis, and merchant segmentation
    (genre/type) drive the platform's category and whitespace analytics.

Source CSV:
    scripts/dataset_generator/master/merchant_master.csv (frozen — 500 rows).

Primary key:
    ``merchant_id`` — natural key issued by the dataset generator
    (MER000001...).

Typical usage:
    Joined (in later phases) against the transaction fact's payee VPA to
    enrich merchant payments with segmentation attributes.
"""

from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class Merchant(Base):
    """A UPI-accepting merchant as defined in the frozen merchant master."""

    __tablename__ = "merchant_master"

    # ------------------------------------------------------------------
    # PRIMARY KEY
    # ------------------------------------------------------------------
    # Natural key from the frozen master (MER000001, MER000002, ...).
    merchant_id: Mapped[str] = mapped_column(String(15), primary_key=True)

    # ------------------------------------------------------------------
    # MERCHANT IDENTITY
    # ------------------------------------------------------------------
    # Trading/display name shown to payers at checkout.
    merchant_name: Mapped[str] = mapped_column(String(50), nullable=False)

    # Bank-attested legal name — the trusted value for merchant-facing
    # reporting; matches payee_verified_name on the transaction fact.
    verified_name: Mapped[str] = mapped_column(String(50), nullable=False)

    # ------------------------------------------------------------------
    # SEGMENTATION
    # ------------------------------------------------------------------
    # Merchant category code (column: mcc) — the ISO four-digit code linking
    # this merchant to its category; indexed because category slicing is a
    # primary analytical path.
    mcc_code: Mapped[str] = mapped_column("mcc", String(4), nullable=False, index=True)

    # Sales channel (ONLINE / OFFLINE / HYBRID).
    merchant_type: Mapped[str] = mapped_column(String(10), nullable=False)

    # Scale/genre segment (AGGREGATOR / LARGE / SMALL).
    merchant_genre: Mapped[str] = mapped_column(String(15), nullable=False)

    # Channel through which the merchant was onboarded (BANK / PSP / APP /
    # AGGREGATOR) — key dimension for onboarding-funnel analytics.
    onboarding_type: Mapped[str] = mapped_column(String(15), nullable=False)

    # ------------------------------------------------------------------
    # PAYMENT IDENTITY (payee-side routing attributes)
    # ------------------------------------------------------------------
    # Merchant virtual payment address (column: payeeaddress) — the join key
    # to the transaction fact's payee VPA; indexed for that lookup path.
    payee_vpa: Mapped[str] = mapped_column(
        "payeeaddress", String(50), nullable=False, index=True
    )

    # Acquiring PSP application and its network org id (columns: payeepsp /
    # payeepsporgid) — the fact table carries only the org id, so the PSP
    # name for a merchant payee is resolved through this master.
    payee_psp_name: Mapped[str] = mapped_column("payeepsp", String(30), nullable=False)
    payee_psp_org_id: Mapped[str] = mapped_column("payeepsporgid", String(10), nullable=False)

    # Settlement bank for the merchant (column: payeebank).
    payee_bank_name: Mapped[str] = mapped_column("payeebank", String(50), nullable=False)

    def __repr__(self) -> str:
        return (
            f"<Merchant(merchant_id={self.merchant_id!r}, "
            f"name={self.merchant_name!r}, "
            f"mcc={self.mcc_code!r})>"
        )
