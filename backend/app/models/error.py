"""Error master ORM model.

Purpose:
    Reference data for the detailed UPI error codes attached to failed
    transactions.

Business role:
    Error codes power the failure analytics suite: error-code Pareto
    charts, bank × error-code heatmaps, technical-decline (TD) versus
    business-decline (BD) splits, and severity-weighted alerting.

Source CSV:
    scripts/dataset_generator/master/error_master.csv (frozen — 139 rows).

Primary key:
    ``errorcode`` — the network error code itself.

Typical usage:
    Joined (in later phases) against the transaction fact's errorcode to
    classify failures by type, owner, severity, and category.
"""

from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class Error(Base):
    """A UPI failure error code as defined in the frozen error master."""

    __tablename__ = "error_master"

    # ------------------------------------------------------------------
    # PRIMARY KEY
    # ------------------------------------------------------------------
    # Network error code ('U30', 'HS1', ...) — the natural key carried
    # verbatim on the transaction fact for failed rows.
    error_code: Mapped[str] = mapped_column("errorcode", String(5), primary_key=True)

    # ------------------------------------------------------------------
    # ERROR CLASSIFICATION
    # ------------------------------------------------------------------
    # Human-readable explanation of the failure.
    description: Mapped[str] = mapped_column(String(100), nullable=False)

    # Decline classification (column: type — TD technical decline / BD
    # business decline) — the primary split in failure analytics. The
    # attribute is named ``error_type`` because ``type`` would shadow the
    # Python built-in; the database column name stays ``type``.
    error_type: Mapped[str] = mapped_column("type", String(5), nullable=False)

    # Participant accountable for the failure (IssuerBank, HSM, NPCI, ...).
    owner: Mapped[str] = mapped_column(String(20), nullable=False)

    # Functional grouping (Authentication, AutoPay, Limits, ...) for rollups.
    category: Mapped[str] = mapped_column(String(30), nullable=False)

    # ------------------------------------------------------------------
    # OPERATIONAL SEMANTICS
    # ------------------------------------------------------------------
    # Whether the failed transaction may be retried — this master encodes
    # the values as the strings 'True'/'False' (unlike the Y/N flags
    # elsewhere), stored with dataset fidelity; boolean conversion belongs
    # to the CSV Import Pipeline / consuming services.
    retryable: Mapped[str] = mapped_column(String(5), nullable=False)

    # Operational severity (CRITICAL / HIGH / MEDIUM / LOW) — weights
    # failure alerts and attention-feed ranking.
    severity: Mapped[str] = mapped_column(String(10), nullable=False)

    def __repr__(self) -> str:
        return (
            f"<Error(error_code={self.error_code!r}, "
            f"type={self.error_type!r}, "
            f"severity={self.severity!r})>"
        )
