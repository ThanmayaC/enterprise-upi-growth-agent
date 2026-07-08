"""Initiation mode master ORM model.

Purpose:
    Reference data for the UPI initiation mode codes describing how a
    transaction was started (QR scan, intent, collect request, ...).

Business role:
    Initiation mode is a core payment-experience dimension: QR-vs-intent
    mix, channel adoption trends, and which entry points support Autopay.

Source CSV:
    scripts/dataset_generator/master/initiation_mode_master.csv
    (frozen — 39 rows).

Primary key:
    ``initiationmode`` — the fixed two-character network mode code.

Typical usage:
    Joined (in later phases) against the transaction fact's initiationmode
    to label entry channels in analytics output.
"""

from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class InitiationMode(Base):
    """A UPI initiation mode code as defined in the frozen mode master."""

    __tablename__ = "initiation_mode_master"

    # ------------------------------------------------------------------
    # PRIMARY KEY
    # ------------------------------------------------------------------
    # Fixed two-character network mode code ('00', '04', '11', ...) — the
    # natural key carried verbatim on the transaction fact.
    initiation_mode: Mapped[str] = mapped_column(
        "initiationmode", String(2), primary_key=True
    )

    # ------------------------------------------------------------------
    # MODE DESCRIPTION
    # ------------------------------------------------------------------
    # Human-readable channel label ('Bharat QR Code', 'Aadhaar', ...).
    description: Mapped[str] = mapped_column(String(50), nullable=False)

    # Broader channel grouping (QR, Contactless, BBPS, ...) for rollups.
    category: Mapped[str] = mapped_column(String(30), nullable=False)

    # ------------------------------------------------------------------
    # AUTOPAY ATTRIBUTES
    # ------------------------------------------------------------------
    # Whether mandates can be initiated through this mode — dataset encodes
    # 'Y'/'N' as a single character, stored with dataset fidelity.
    autopay_supported: Mapped[str] = mapped_column(String(1), nullable=False)

    def __repr__(self) -> str:
        return (
            f"<InitiationMode(initiation_mode={self.initiation_mode!r}, "
            f"description={self.description!r})>"
        )
