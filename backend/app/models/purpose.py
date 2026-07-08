"""Purpose master ORM model.

Purpose:
    Reference data for the UPI purpose codes describing why a payment was
    made (Default, BBPS, Insurance, SEBI, ...).

Business role:
    Purpose codes distinguish plain payments from specialized flows and
    carry the recurring/Autopay potential of each flow — inputs to the
    Autopay opportunity analytics.

Source CSV:
    scripts/dataset_generator/master/purpose_master.csv (frozen — 78 rows).

Primary key:
    ``purposecode`` — the fixed two-character network purpose code.

Typical usage:
    Joined (in later phases) against the transaction fact's purposecode to
    label purpose categories in analytics output.
"""

from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class Purpose(Base):
    """A UPI payment purpose code as defined in the frozen purpose master."""

    __tablename__ = "purpose_master"

    # ------------------------------------------------------------------
    # PRIMARY KEY
    # ------------------------------------------------------------------
    # Fixed two-character network purpose code ('00', '01', ...) — the
    # natural key carried verbatim on the transaction fact.
    purpose_code: Mapped[str] = mapped_column("purposecode", String(2), primary_key=True)

    # ------------------------------------------------------------------
    # PURPOSE DESCRIPTION
    # ------------------------------------------------------------------
    # Human-readable purpose label (column: purpose — 'B2B Business
    # Payments', 'BBPS', ...).
    purpose: Mapped[str] = mapped_column(String(80), nullable=False)

    # Broader purpose grouping (ATM, AutoPay, BBPS, ...) for rollups.
    category: Mapped[str] = mapped_column(String(30), nullable=False)

    # ------------------------------------------------------------------
    # AUTOPAY ATTRIBUTES
    # ------------------------------------------------------------------
    # Qualitative Autopay potential of this purpose (Very High / High /
    # Medium / Low) — feeds Autopay opportunity discovery.
    autopay_potential: Mapped[str] = mapped_column(String(15), nullable=False)

    # Whether this purpose is inherently recurring — dataset encodes
    # 'Y'/'N' as a single character, stored with dataset fidelity.
    recurring: Mapped[str] = mapped_column(String(1), nullable=False)

    def __repr__(self) -> str:
        return (
            f"<Purpose(purpose_code={self.purpose_code!r}, "
            f"purpose={self.purpose!r}, "
            f"category={self.category!r})>"
        )
