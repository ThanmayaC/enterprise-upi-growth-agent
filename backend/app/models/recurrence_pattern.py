"""Recurrence pattern master ORM model.

Purpose:
    Reference data for the Autopay mandate recurrence patterns
    (DAILY, MONTHLY, FORTNIGHTLY, ASPRESENTED, ...).

Business role:
    Recurrence patterns describe the cadence of mandate executions —
    a segmentation axis for Autopay revenue-predictability analytics.

Source CSV:
    scripts/dataset_generator/master/recurrence_pattern_master.csv
    (frozen — 8 rows).

Primary key:
    ``recurrencepattern`` — the pattern keyword itself.

Typical usage:
    Joined (in later phases) against the transaction fact's
    recurrencepattern to label mandate cadences in analytics output.
"""

from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class RecurrencePattern(Base):
    """An Autopay mandate recurrence pattern from the frozen master."""

    __tablename__ = "recurrence_pattern_master"

    # ------------------------------------------------------------------
    # PRIMARY KEY
    # ------------------------------------------------------------------
    # Pattern keyword (MONTHLY, ASPRESENTED, ...) — the natural key carried
    # verbatim on the transaction fact for mandate rows.
    recurrence_pattern: Mapped[str] = mapped_column(
        "recurrencepattern", String(15), primary_key=True
    )

    # ------------------------------------------------------------------
    # PATTERN DESCRIPTION
    # ------------------------------------------------------------------
    # Human-readable explanation of the execution cadence.
    description: Mapped[str] = mapped_column(String(50), nullable=False)

    def __repr__(self) -> str:
        return (
            f"<RecurrencePattern(recurrence_pattern={self.recurrence_pattern!r}, "
            f"description={self.description!r})>"
        )
