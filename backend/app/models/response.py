"""Response master ORM model.

Purpose:
    Reference data for the UPI network response codes and their terminal
    outcomes ('00' = approved, 'U30' = debit failed, ...).

Business role:
    Response codes are the authoritative mapping from wire-level results to
    the SUCCESS/FAILURE outcome that defines the platform's success-rate
    KPI, including which party owns each outcome and whether it can be
    retried.

Source CSV:
    scripts/dataset_generator/master/response_master.csv (frozen — 14 rows).

Primary key:
    ``responsecode`` — the network response code itself.

Typical usage:
    Joined (in later phases) against the transaction fact's responsecode
    to label outcomes and attribute failures to owning participants.
"""

from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class Response(Base):
    """A UPI network response code as defined in the frozen response master."""

    __tablename__ = "response_master"

    # ------------------------------------------------------------------
    # PRIMARY KEY
    # ------------------------------------------------------------------
    # Network response code ('00', 'U16', 'U30', ...) — the natural key
    # carried verbatim on the transaction fact.
    response_code: Mapped[str] = mapped_column("responsecode", String(5), primary_key=True)

    # ------------------------------------------------------------------
    # OUTCOME CLASSIFICATION
    # ------------------------------------------------------------------
    # Terminal outcome this code maps to (column: responseresult — SUCCESS /
    # FAILURE) — the ground truth behind the success-rate KPI.
    response_result: Mapped[str] = mapped_column("responseresult", String(10), nullable=False)

    # Human-readable explanation of the response.
    description: Mapped[str] = mapped_column(String(80), nullable=False)

    # ------------------------------------------------------------------
    # OWNERSHIP & RETRY SEMANTICS
    # ------------------------------------------------------------------
    # Participant accountable for this outcome (IssuerBank, PayerPSP,
    # NPCI, ...) — drives failure attribution in reliability analytics.
    owner: Mapped[str] = mapped_column(String(20), nullable=False)

    # Whether the transaction may be retried after this response — dataset
    # encodes 'Y'/'N' as a single character, stored with dataset fidelity.
    retryable: Mapped[str] = mapped_column(String(1), nullable=False)

    def __repr__(self) -> str:
        return (
            f"<Response(response_code={self.response_code!r}, "
            f"result={self.response_result!r}, "
            f"owner={self.owner!r})>"
        )
