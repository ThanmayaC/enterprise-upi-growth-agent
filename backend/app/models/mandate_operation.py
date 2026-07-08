"""Mandate operation master ORM model.

Purpose:
    Reference data for the Autopay mandate lifecycle operations
    (CREATE, UPDATE, PAUSE, UNPAUSE, REVOKE).

Business role:
    Mandate operations define the stages of the Autopay lifecycle funnel —
    the basis for mandate creation/retention/revocation analytics.

Source CSV:
    scripts/dataset_generator/master/mandate_operation_master.csv
    (frozen — 5 rows).

Primary key:
    ``mandateoperation`` — the operation keyword itself.

Typical usage:
    Joined (in later phases) against the transaction fact's
    mandateoperation to label lifecycle stages in funnel analytics.
"""

from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class MandateOperation(Base):
    """An Autopay mandate lifecycle operation from the frozen master."""

    __tablename__ = "mandate_operation_master"

    # ------------------------------------------------------------------
    # PRIMARY KEY
    # ------------------------------------------------------------------
    # Operation keyword (CREATE, PAUSE, ...) — the natural key carried
    # verbatim on the transaction fact for mandate rows.
    mandate_operation: Mapped[str] = mapped_column(
        "mandateoperation", String(10), primary_key=True
    )

    # ------------------------------------------------------------------
    # OPERATION DESCRIPTION
    # ------------------------------------------------------------------
    # Human-readable explanation of the lifecycle stage.
    description: Mapped[str] = mapped_column(String(50), nullable=False)

    def __repr__(self) -> str:
        return (
            f"<MandateOperation(mandate_operation={self.mandate_operation!r}, "
            f"description={self.description!r})>"
        )
