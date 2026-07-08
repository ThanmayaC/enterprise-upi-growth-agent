"""Transaction ORM model — the UPI transaction fact table.

Maps the ``fact_upi_transactions`` table defined in the frozen Database
Architecture v1.0 with strict dataset fidelity: every mapped attribute
corresponds to exactly one of the 57 columns of the frozen transaction
dataset — no invented columns, no derived columns, no surrogate identifiers.

Design notes (per the frozen architecture — do not alter here):
- ``txnid`` is the natural primary key. The UPI network guarantees its
  uniqueness, so no surrogate key exists in the schema.
- Attribute names are Python-friendly for readable application code, but
  every ``mapped_column`` pins the original frozen database column name
  (e.g. ``transaction_id`` maps to the ``txnid`` column). The physical
  schema therefore matches the dataset byte-for-byte.
- String lengths are validated against the full frozen dataset (1,012,591
  rows): fixed-width code fields (MCC, purpose code, initiation mode,
  response code, mobile, Y/N flag) use their exact width; variable text
  fields use the observed maximum plus enterprise headroom.
- ``revokable`` arrives as ``Y``/``N`` in the dataset, so it is mapped as
  ``String(1)``; conversion to a proper boolean is the responsibility of
  consumers, not the schema (see the CSV Import Pipeline note on the field).
- Entity attributes (bank names, PSP names, MCC) are stored denormalized as
  they arrive from the network feed. ``ForeignKey`` constraints and
  ``relationship()`` mappings are added only after the master models exist.
- Nullability mirrors the dataset exactly (verified over the full file):
  mandate lifecycle fields are populated only for mandate/Autopay rows,
  merchant fields only for merchant payees, amounts only for financial
  transactions, and ``errorcode`` only on failures.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Integer, Numeric, String, Text, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base




class Transaction(Base):
    """A single UPI transaction (financial or mandate lifecycle operation).

    Covers every transaction flavour in the frozen dataset: P2P payments,
    merchant/BBPS/collect payments, and the full Autopay mandate lifecycle
    (registration, execution, retry, pause, resume, update, revoke).
    """

    __tablename__ = "fact_upi_transactions"

    # ------------------------------------------------------------------
    # PRIMARY KEY
    # ------------------------------------------------------------------
    # UPI network transaction id (column: txnid) — the natural primary key
    # per the frozen architecture. Uniqueness is guaranteed upstream by the
    # network, so the business identifier is also the row identity.
    transaction_id: Mapped[str] = mapped_column("txnid", String(50), primary_key=True)

    # ------------------------------------------------------------------
    # TRANSACTION INFORMATION
    # ------------------------------------------------------------------
    # Business classification (P2P_PAYMENT, MERCHANT_PAYMENT, AUTOPAY_*,
    # MANDATE_*, ...). Primary slicing dimension for product-mix analytics.
    transaction_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)

    # Network-level category (column: txntype — Financial / NonFinancial).
    # Separates money movement from mandate/administrative operations.
    transaction_category: Mapped[str] = mapped_column("txntype", String(15), nullable=False)

    # Exact event time (column: ts) — basis for intraday/hourly analysis.
    transaction_timestamp: Mapped[datetime] = mapped_column("ts", DateTime, nullable=False)

    # Calendar date (column: txndate), carried alongside the timestamp in the
    # frozen schema so daily aggregation groups on an indexed date column.
    transaction_date: Mapped[date] = mapped_column("txndate", Date, nullable=False, index=True)

    # Customer reference number (column: custrefno) — the retrieval reference
    # customers quote in disputes and support flows. Present on every row.
    customer_reference_number: Mapped[str] = mapped_column(
        "custrefno", String(25), nullable=False
    )

    # Purpose of payment (columns: purpose / purposecode) — distinguishes
    # default payments from specialized flows (SEBI, Insurance, ...).
    # The purpose code is a fixed two-character network code.
    purpose: Mapped[str] = mapped_column(String(30), nullable=False)
    purpose_code: Mapped[str] = mapped_column("purposecode", String(2), nullable=False)

    # How the transaction was initiated (column: initiationmode — a fixed
    # two-character network code: QR, intent, collect, ...) and by which
    # side (column: initiatedby — PAYER/PAYEE). Key dimensions for
    # payment-experience analytics.
    initiation_mode: Mapped[str] = mapped_column("initiationmode", String(2), nullable=False)
    initiated_by: Mapped[str] = mapped_column("initiatedby", String(5), nullable=False)

    # Credential used to authorize the transaction (columns: cred_type /
    # cred_subtype, plus the optional secondary factor pair) — powers
    # authentication-mix and credential-level failure analysis.
    credential_type: Mapped[str] = mapped_column("cred_type", String(15), nullable=False)
    credential_subtype: Mapped[str] = mapped_column("cred_subtype", String(15), nullable=False)
    credential_type_secondary: Mapped[str | None] = mapped_column(
        "cred_type_secondary", String(15), nullable=True
    )
    credential_subtype_secondary: Mapped[str | None] = mapped_column(
        "cred_subtype_secondary", String(15), nullable=True
    )

    # Free-text note supplied by the initiator (column: txnnote).
    transaction_note: Mapped[str] = mapped_column("txnnote", Text, nullable=False)

    # ------------------------------------------------------------------
    # CUSTOMER INFORMATION (payer / remitter side)
    # ------------------------------------------------------------------
    # Payer virtual payment address (column: payeraddress) — the customer's
    # UPI identity as seen by the network.
    payer_vpa: Mapped[str] = mapped_column("payeraddress", String(50), nullable=False)

    # Remitter account context (columns: remitteracctype / remitterorgid) —
    # the debit-side account type and owning organization.
    remitter_account_type: Mapped[str] = mapped_column(
        "remitteracctype", String(10), nullable=False
    )
    remitter_org_id: Mapped[str] = mapped_column("remitterorgid", String(10), nullable=False)

    # Payer-side network descriptors (columns: pracctype, prcode, prorgid,
    # prdmobile) — account type, participant code, org id, and the 10-digit
    # registered mobile used in payer-side reconciliation.
    payer_account_type: Mapped[str] = mapped_column("pracctype", String(10), nullable=False)
    payer_code: Mapped[str] = mapped_column("prcode", String(10), nullable=False)
    payer_org_id: Mapped[str] = mapped_column("prorgid", String(10), nullable=False)
    payer_mobile: Mapped[str] = mapped_column("prdmobile", String(10), nullable=False)

    # ------------------------------------------------------------------
    # MERCHANT INFORMATION (payee side)
    # ------------------------------------------------------------------
    # Payee virtual payment address and names (columns: payeeaddress,
    # payeename, payee_verified_name). The verified name is the attested
    # legal name — the trusted value for payee-facing reporting.
    payee_vpa: Mapped[str] = mapped_column("payeeaddress", String(50), nullable=False)
    payee_name: Mapped[str] = mapped_column("payeename", String(50), nullable=False)
    payee_verified_name: Mapped[str] = mapped_column(String(50), nullable=False)

    # Payee classification (column: payeetype — PERSON / MERCHANT). Drives
    # the P2P-vs-P2M split without requiring a master join.
    payee_type: Mapped[str] = mapped_column("payeetype", String(10), nullable=False)

    # Merchant category code (column: payeemcc) — a fixed four-digit ISO
    # code; primary dimension for category penetration and whitespace
    # analytics. Null for PERSON payees.
    mcc_code: Mapped[str | None] = mapped_column("payeemcc", String(4), nullable=True, index=True)

    # Merchant segmentation attributes (columns: payeemerchantgenre,
    # payeemerchanttype, payeeonboardingtype) — genre (aggregator/small),
    # channel (online/offline), and onboarding route. Null for PERSON payees.
    merchant_genre: Mapped[str | None] = mapped_column(
        "payeemerchantgenre", String(15), nullable=True
    )
    merchant_type: Mapped[str | None] = mapped_column(
        "payeemerchanttype", String(10), nullable=True
    )
    merchant_onboarding_type: Mapped[str | None] = mapped_column(
        "payeeonboardingtype", String(15), nullable=True
    )

    # Payee-side network descriptors (columns: pycode, pyorgid, pyrefaddr).
    payee_code: Mapped[str] = mapped_column("pycode", String(10), nullable=False)
    payee_org_id: Mapped[str] = mapped_column("pyorgid", String(10), nullable=False)
    payee_reference_address: Mapped[str] = mapped_column(
        "pyrefaddr", String(50), nullable=False
    )

    # ------------------------------------------------------------------
    # BANK INFORMATION
    # ------------------------------------------------------------------
    # Debit and credit bank names as reported by the network (columns:
    # payerbank / payeebank). Indexed: bank-level success-rate and failure
    # decomposition are the platform's hottest diagnostic paths.
    payer_bank: Mapped[str] = mapped_column(
        "payerbank", String(50), nullable=False, index=True
    )
    payee_bank: Mapped[str] = mapped_column(
        "payeebank", String(50), nullable=False, index=True
    )

    # Sponsor banks backing each side's PSP (columns: payer_psp_bank /
    # payee_psp_bank) — needed to separate issuer-bank failures from
    # PSP-sponsor-bank failures in reliability analytics.
    payer_psp_sponsor_bank: Mapped[str] = mapped_column(
        "payer_psp_bank", String(50), nullable=False
    )
    payee_psp_sponsor_bank: Mapped[str] = mapped_column(
        "payee_psp_bank", String(50), nullable=False
    )

    # ------------------------------------------------------------------
    # PSP INFORMATION
    # ------------------------------------------------------------------
    # Payer-side PSP application (column: payerpsp). Indexed for PSP
    # leaderboards and PSP-level failure heatmaps. The frozen schema carries
    # the payee PSP via its org id only (payeepsporgid, below).
    payer_psp: Mapped[str] = mapped_column(
        "payerpsp", String(30), nullable=False, index=True
    )

    # PSP organization ids as reported on the wire (columns: payerpsporgid /
    # payeepsporgid) — kept verbatim for reconciliation with network reports.
    payer_psp_org_id: Mapped[str] = mapped_column("payerpsporgid", String(10), nullable=False)
    payee_psp_org_id: Mapped[str] = mapped_column("payeepsporgid", String(10), nullable=False)

    # The PSP that actually initiated the request (columns: initiatorpsp /
    # initiatorpsporgid) — may differ from the payer PSP in collect flows.
    initiator_psp: Mapped[str] = mapped_column("initiatorpsp", String(30), nullable=False)
    initiator_psp_org_id: Mapped[str] = mapped_column(
        "initiatorpsporgid", String(10), nullable=False
    )

    # ------------------------------------------------------------------
    # MANDATE INFORMATION (Autopay lifecycle — null for non-mandate rows)
    # ------------------------------------------------------------------
    # Unique Mandate Number (column: umn) — joins every lifecycle event
    # (create, execute, pause, revoke) of one mandate for funnel analytics.
    unique_mandate_number: Mapped[str | None] = mapped_column(
        "umn", String(30), nullable=True, index=True
    )

    # Execution ordinal within the mandate (column: payerseqnum) — which
    # installment an Autopay execution/retry represents.
    payer_sequence_number: Mapped[int | None] = mapped_column(
        "payerseqnum", Integer, nullable=True
    )

    # Lifecycle operation (column: mandateoperation — CREATE, EXECUTE, ...).
    mandate_operation: Mapped[str | None] = mapped_column(
        "mandateoperation", String(10), nullable=True
    )

    # Mandate validity window (columns: validitystart / validityend) —
    # bounds the period in which executions are permitted.
    mandate_validity_start: Mapped[date | None] = mapped_column(
        "validitystart", Date, nullable=True
    )
    mandate_validity_end: Mapped[date | None] = mapped_column(
        "validityend", Date, nullable=True
    )

    # Recurrence rule (column: recurrencepattern — MONTHLY, FORTNIGHTLY, ...).
    recurrence_pattern: Mapped[str | None] = mapped_column(
        "recurrencepattern", String(15), nullable=True
    )

    # When the mandate execution actually fired (column: umnexects).
    mandate_execution_timestamp: Mapped[datetime | None] = mapped_column(
        "umnexects", DateTime, nullable=True
    )

    # Whether the customer may revoke the mandate (column: revokable). The
    # frozen dataset encodes this as the single characters 'Y' / 'N', NOT as
    # a boolean, so it is stored with dataset fidelity as String(1).
    # Conversion to a real boolean is performed by the CSV Import Pipeline /
    # consuming services — never by this schema.
    revokable_flag: Mapped[str | None] = mapped_column("revokable", String(1), nullable=True)

    # ------------------------------------------------------------------
    # FINANCIAL INFORMATION
    # ------------------------------------------------------------------
    # Amounts as exact decimals (columns: txamount / payeeamt) — floats are
    # never acceptable for money. Nullable because non-financial mandate
    # operations (registration, pause, revoke) carry no amount.
    transaction_amount: Mapped[Decimal | None] = mapped_column(
        "txamount", Numeric(15, 2), nullable=True
    )
    payee_amount: Mapped[Decimal | None] = mapped_column(
        "payeeamt", Numeric(15, 2), nullable=True
    )

    # ------------------------------------------------------------------
    # STATUS INFORMATION
    # ------------------------------------------------------------------
    # Network response code (column: responsecode — '00' means approved).
    response_code: Mapped[str] = mapped_column("responsecode", String(3), nullable=False)

    # Terminal outcome (column: responseresult — SUCCESS / FAILURE / ...).
    # Indexed: it is the numerator/denominator of the success-rate KPI, the
    # platform's most-queried metric.
    status: Mapped[str] = mapped_column(
        "responseresult", String(10), nullable=False, index=True
    )

    # Failure classification (column: errorcode) — null on success. Feeds the
    # error-code Pareto and bank × error-code failure heatmaps.
    error_code: Mapped[str | None] = mapped_column("errorcode", String(5), nullable=True)

    # Human-readable final status text (column: currstatusdesc).
    current_status_description: Mapped[str] = mapped_column(
        "currstatusdesc", String(50), nullable=False
    )

    # ------------------------------------------------------------------
    # AUDIT INFORMATION
    # ------------------------------------------------------------------
    # Upstream as-of/settlement timestamp (column: asdt) — the data version
    # the row belongs to; drives the platform's freshness indicators.
    as_of_timestamp: Mapped[datetime] = mapped_column("asdt", DateTime, nullable=False)

    def __repr__(self) -> str:
        return (
            f"<Transaction(transaction_id={self.transaction_id!r}, "
            f"type={self.transaction_type!r}, "
            f"date={self.transaction_date!r}, "
            f"amount={self.transaction_amount!r}, "
            f"status={self.status!r})>"
        )
