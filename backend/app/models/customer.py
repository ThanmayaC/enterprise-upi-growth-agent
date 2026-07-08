"""Customer master ORM model.

Purpose:
    Reference data for every retail customer (payer) in the frozen dataset.

Business role:
    Customers are the payer side of virtually all UPI flows. Customer-level
    attributes (home bank, PSP, account type) support adoption, cohort, and
    payer-behaviour analytics.

Source CSV:
    scripts/dataset_generator/master/customer_master.csv
    (frozen — 150,000 rows).

Primary key:
    ``customer_id`` — natural key issued by the dataset generator
    (CUST0000001...).

Typical usage:
    Joined (in later phases) against the transaction fact's payer VPA to
    attribute transactions to customers.
"""

from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class Customer(Base):
    """A UPI retail customer as defined in the frozen customer master."""

    __tablename__ = "customer_master"

    # ------------------------------------------------------------------
    # PRIMARY KEY
    # ------------------------------------------------------------------
    # Natural key from the frozen master (CUST0000001, ...).
    customer_id: Mapped[str] = mapped_column(String(15), primary_key=True)

    # ------------------------------------------------------------------
    # CUSTOMER IDENTITY
    # ------------------------------------------------------------------
    # Customer display name.
    customer_name: Mapped[str] = mapped_column(String(50), nullable=False)

    # Customer virtual payment address (column: payeraddress) — the join key
    # to the transaction fact's payer VPA; indexed for that lookup path on
    # this 150k-row master.
    payer_vpa: Mapped[str] = mapped_column(
        "payeraddress", String(50), nullable=False, index=True
    )

    # Registered mobile number (10 digits in the frozen dataset).
    mobile: Mapped[str] = mapped_column(String(10), nullable=False)

    # ------------------------------------------------------------------
    # PSP CONTEXT (application side)
    # ------------------------------------------------------------------
    # Home PSP application and its network org id (columns: payerpsp /
    # payerpsporgid) — the app through which this customer transacts.
    payer_psp_name: Mapped[str] = mapped_column("payerpsp", String(30), nullable=False)
    payer_psp_org_id: Mapped[str] = mapped_column("payerpsporgid", String(10), nullable=False)

    # Bank whose VPA handle the customer uses (column: payerbank).
    payer_bank_name: Mapped[str] = mapped_column("payerbank", String(50), nullable=False)

    # ------------------------------------------------------------------
    # REMITTER CONTEXT (funding account side)
    # ------------------------------------------------------------------
    # Bank and org id actually holding the debit account (columns:
    # remitter_bank / remitterorgid) — may differ from the PSP-handle bank.
    remitter_bank_name: Mapped[str] = mapped_column("remitter_bank", String(50), nullable=False)
    remitter_org_id: Mapped[str] = mapped_column("remitterorgid", String(10), nullable=False)

    # Funding account type (column: remitteracctype — SAVINGS, CURRENT, NRE,
    # NRO, CC, PPI, ...) — segmentation axis for payer-behaviour analytics.
    remitter_account_type: Mapped[str] = mapped_column(
        "remitteracctype", String(10), nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"<Customer(customer_id={self.customer_id!r}, "
            f"name={self.customer_name!r}, "
            f"vpa={self.payer_vpa!r})>"
        )
