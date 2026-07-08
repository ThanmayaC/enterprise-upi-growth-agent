"""MCC (Merchant Category Code) master ORM model.

Purpose:
    Reference data for the ISO merchant category codes used in the frozen
    dataset.

Business role:
    MCC is the primary dimension for category penetration, whitespace, and
    Autopay-potential analytics. Every merchant payment on the fact table
    carries an MCC (column payeemcc).

Source CSV:
    scripts/dataset_generator/master/mcc_master.csv (frozen — 30 rows).

Primary key:
    ``mcc`` — the ISO four-digit category code itself.

Typical usage:
    Joined (in later phases) against the transaction fact's payeemcc and
    the merchant master's mcc to label categories in analytics output.
"""

from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class Mcc(Base):
    """A merchant category code as defined in the frozen MCC master."""

    __tablename__ = "mcc_master"

    # ------------------------------------------------------------------
    # PRIMARY KEY
    # ------------------------------------------------------------------
    # The ISO four-digit merchant category code (4111, 5411, ...) — a
    # fixed-width natural key.
    mcc_code: Mapped[str] = mapped_column("mcc", String(4), primary_key=True)

    # ------------------------------------------------------------------
    # CATEGORY DESCRIPTION
    # ------------------------------------------------------------------
    # Human-readable category label (Groceries, Airlines, Utilities, ...).
    category: Mapped[str] = mapped_column(String(50), nullable=False)

    # ------------------------------------------------------------------
    # AUTOPAY ATTRIBUTES
    # ------------------------------------------------------------------
    # Whether mandates are possible in this category — dataset encodes
    # 'Y'/'N' as a single character, stored with dataset fidelity.
    autopay_possible: Mapped[str] = mapped_column(String(1), nullable=False)

    # Strategic Autopay priority for the category (HIGH / MEDIUM / LOW) —
    # feeds Autopay opportunity discovery.
    autopay_priority: Mapped[str] = mapped_column(String(10), nullable=False)

    def __repr__(self) -> str:
        return (
            f"<Mcc(mcc_code={self.mcc_code!r}, "
            f"category={self.category!r}, "
            f"autopay_priority={self.autopay_priority!r})>"
        )
