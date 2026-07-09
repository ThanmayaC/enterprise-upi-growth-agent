"""Transaction repository — optimized access to the UPI transaction fact.

Purpose:
    Every read path into ``fact_upi_transactions`` (1M+ rows today, designed
    for 10M+). Exposes composable lookups, filtered listings, counts, sums,
    and grouped aggregates that the Phase 7 Service Layer will combine into
    analytics — the repository itself computes nothing business-specific.

Enterprise notes:
    - All listing methods share one pagination/ordering path and default to
      a bounded page (:data:`DEFAULT_PAGE_SIZE`) so no caller can
      accidentally materialize millions of ORM objects; pass
      ``limit=None`` deliberately to remove the bound.
    - All aggregate methods share one filter builder
      (``_apply_transaction_filters``) and one grouping engine
      (``_group_and_measure``) — six public group-by methods, zero
      duplicated query logic. Aggregation happens in PostgreSQL; only the
      grouped result rows travel to Python.
    - ``stream_transactions`` exists for future full-table scans (feature
      engineering, exports): it yields server-side batches via
      ``yield_per`` with constant memory.
    - Identity conventions of the frozen schema: a *customer* is identified
      by the payer VPA (``payeraddress``), a *merchant* by the payee VPA
      (``payeeaddress``); banks and PSPs are carried denormalized by name.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Iterator, Sequence

from sqlalchemy import Row, Select, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import InstrumentedAttribute

from app.models import Transaction
from app.repositories.base_repository import (
    BaseRepository,
    InvalidFilterError,
)

#: Bounded default page for listing methods — a safety net at fact-table scale.
DEFAULT_PAGE_SIZE = 100

#: Server-side fetch size used by :meth:`TransactionRepository.stream_transactions`.
DEFAULT_STREAM_BATCH_SIZE = 10_000

#: Sides of a transaction on which a bank or PSP can appear.
_SIDES = ("payer", "payee")


class TransactionRepository(BaseRepository[Transaction]):
    """Read-only repository for the ``fact_upi_transactions`` table."""

    model = Transaction

    # ------------------------------------------------------------------
    # Single-record access
    # ------------------------------------------------------------------
    def get_transaction_by_id(self, transaction_id: str) -> Transaction | None:
        """Fetch one transaction by its UPI network id (primary key).

        Purpose:
            Point lookup for dispute/support and detail views.

        Parameters:
            transaction_id: The ``txnid`` value.

        Returns:
            The transaction, or ``None`` if it does not exist.
        """

        return self.find_by_id(transaction_id)

    # ------------------------------------------------------------------
    # Filtered listings (all bounded and paginated)
    # ------------------------------------------------------------------
    def get_transactions(
        self,
        *,
        limit: int | None = DEFAULT_PAGE_SIZE,
        offset: int = 0,
        order_by: str = "transaction_timestamp",
        descending: bool = False,
    ) -> Sequence[Transaction]:
        """List transactions with ordering and pagination.

        Purpose:
            Generic paged access over the whole fact table.

        Parameters:
            limit: Page size (``None`` removes the bound — use deliberately).
            offset: Rows to skip.
            order_by: Model attribute to order on (validated).
            descending: Order direction.

        Returns:
            One page of transactions.
        """

        return self._list(select(Transaction), limit, offset, order_by, descending)

    def get_transactions_by_date(
        self, day: date, *, limit: int | None = DEFAULT_PAGE_SIZE, offset: int = 0
    ) -> Sequence[Transaction]:
        """List transactions of one calendar day.

        Purpose:
            Daily drill-down; hits the indexed ``txndate`` column.

        Parameters:
            day: The transaction date.
            limit: Page size (``None`` = unbounded).
            offset: Rows to skip.

        Returns:
            The day's transactions, chronologically ordered.
        """

        stmt = select(Transaction).where(Transaction.transaction_date == day)
        return self._list(stmt, limit, offset, "transaction_timestamp", False)

    def get_transactions_between_dates(
        self,
        start_date: date,
        end_date: date,
        *,
        limit: int | None = DEFAULT_PAGE_SIZE,
        offset: int = 0,
    ) -> Sequence[Transaction]:
        """List transactions within an inclusive date range.

        Purpose:
            Period drill-down over the indexed date column.

        Parameters:
            start_date: First day of the range (inclusive).
            end_date: Last day of the range (inclusive).
            limit: Page size (``None`` = unbounded).
            offset: Rows to skip.

        Returns:
            The period's transactions, chronologically ordered.

        Raises:
            InvalidFilterError: If ``start_date`` is after ``end_date``.
        """

        stmt = self._apply_transaction_filters(
            select(Transaction), start_date=start_date, end_date=end_date
        )
        return self._list(stmt, limit, offset, "transaction_timestamp", False)

    def get_transactions_by_customer(
        self,
        customer_vpa: str,
        *,
        limit: int | None = DEFAULT_PAGE_SIZE,
        offset: int = 0,
    ) -> Sequence[Transaction]:
        """List transactions initiated by one customer (payer VPA).

        Purpose:
            Customer activity history.

        Parameters:
            customer_vpa: The customer's UPI address (``payeraddress``).
            limit: Page size (``None`` = unbounded).
            offset: Rows to skip.

        Returns:
            The customer's transactions, most recent first.
        """

        stmt = select(Transaction).where(Transaction.payer_vpa == customer_vpa)
        return self._list(stmt, limit, offset, "transaction_timestamp", True)

    def get_transactions_by_merchant(
        self,
        merchant_vpa: str,
        *,
        limit: int | None = DEFAULT_PAGE_SIZE,
        offset: int = 0,
    ) -> Sequence[Transaction]:
        """List transactions received by one merchant (payee VPA).

        Purpose:
            Merchant activity history.

        Parameters:
            merchant_vpa: The merchant's UPI address (``payeeaddress``).
            limit: Page size (``None`` = unbounded).
            offset: Rows to skip.

        Returns:
            The merchant's transactions, most recent first.
        """

        stmt = select(Transaction).where(Transaction.payee_vpa == merchant_vpa)
        return self._list(stmt, limit, offset, "transaction_timestamp", True)

    def get_transactions_by_bank(
        self,
        bank_name: str,
        *,
        side: str = "payer",
        limit: int | None = DEFAULT_PAGE_SIZE,
        offset: int = 0,
    ) -> Sequence[Transaction]:
        """List transactions where a bank appears on one side.

        Purpose:
            Bank-level drill-down on the indexed bank-name columns.

        Parameters:
            bank_name: Bank display name as carried on the fact.
            side: ``"payer"`` (debit side) or ``"payee"`` (credit side).
            limit: Page size (``None`` = unbounded).
            offset: Rows to skip.

        Returns:
            The bank's transactions, most recent first.

        Raises:
            InvalidFilterError: For an unknown ``side``.
        """

        stmt = select(Transaction).where(self._bank_column(side) == bank_name)
        return self._list(stmt, limit, offset, "transaction_timestamp", True)

    def get_transactions_by_psp(
        self,
        psp_name: str,
        *,
        limit: int | None = DEFAULT_PAGE_SIZE,
        offset: int = 0,
    ) -> Sequence[Transaction]:
        """List transactions initiated through one payer-side PSP app.

        Purpose:
            PSP-level drill-down on the indexed ``payerpsp`` column. (The
            frozen schema carries the payee PSP only as an org id, so PSP
            queries are payer-side by design.)

        Parameters:
            psp_name: PSP display name (e.g. as in ``psp_master``).
            limit: Page size (``None`` = unbounded).
            offset: Rows to skip.

        Returns:
            The PSP's transactions, most recent first.
        """

        stmt = select(Transaction).where(Transaction.payer_psp == psp_name)
        return self._list(stmt, limit, offset, "transaction_timestamp", True)

    def get_transactions_by_status(
        self,
        status: str,
        *,
        limit: int | None = DEFAULT_PAGE_SIZE,
        offset: int = 0,
    ) -> Sequence[Transaction]:
        """List transactions by terminal outcome (``responseresult``).

        Purpose:
            Outcome drill-down (e.g. failures) on the indexed status column.

        Parameters:
            status: Outcome value as stored (e.g. ``SUCCESS``, ``FAILURE``).
            limit: Page size (``None`` = unbounded).
            offset: Rows to skip.

        Returns:
            The matching transactions, most recent first.
        """

        stmt = select(Transaction).where(Transaction.status == status)
        return self._list(stmt, limit, offset, "transaction_timestamp", True)

    def get_transactions_by_mcc(
        self,
        mcc_code: str,
        *,
        limit: int | None = DEFAULT_PAGE_SIZE,
        offset: int = 0,
    ) -> Sequence[Transaction]:
        """List merchant transactions of one category code.

        Purpose:
            Category drill-down on the indexed ``payeemcc`` column.

        Parameters:
            mcc_code: Four-digit merchant category code.
            limit: Page size (``None`` = unbounded).
            offset: Rows to skip.

        Returns:
            The category's transactions, most recent first.
        """

        stmt = select(Transaction).where(Transaction.mcc_code == mcc_code)
        return self._list(stmt, limit, offset, "transaction_timestamp", True)

    # ------------------------------------------------------------------
    # Scalar aggregates
    # ------------------------------------------------------------------
    def count_transactions(
        self,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        status: str | None = None,
    ) -> int:
        """Count transactions, optionally within a period and/or outcome.

        Purpose:
            The counting primitive future KPIs are built from; counting
            happens entirely in the database.

        Parameters:
            start_date: First day (inclusive), or ``None``.
            end_date: Last day (inclusive), or ``None``.
            status: Outcome filter, or ``None``.

        Returns:
            The matching row count.
        """

        stmt = self._apply_transaction_filters(
            select(func.count()).select_from(Transaction),
            start_date=start_date,
            end_date=end_date,
            status=status,
        )
        return int(self._execute_scalar(stmt) or 0)

    def sum_transaction_amount(
        self,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        status: str | None = None,
    ) -> Decimal:
        """Sum transaction amounts, optionally within a period and/or outcome.

        Purpose:
            The volume primitive future KPIs are built from. Non-financial
            rows carry ``NULL`` amounts and are excluded by SQL ``SUM``.

        Parameters:
            start_date: First day (inclusive), or ``None``.
            end_date: Last day (inclusive), or ``None``.
            status: Outcome filter, or ``None``.

        Returns:
            The exact ``Decimal`` total (``0`` when nothing matches).
        """

        stmt = self._apply_transaction_filters(
            select(func.sum(Transaction.transaction_amount)),
            start_date=start_date,
            end_date=end_date,
            status=status,
        )
        total = self._execute_scalar(stmt)
        return total if total is not None else Decimal("0")

    # ------------------------------------------------------------------
    # Grouped aggregates (count + total amount per group)
    # ------------------------------------------------------------------
    def group_by_day(
        self,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        status: str | None = None,
    ) -> Sequence[Row[Any]]:
        """Aggregate transactions per calendar day.

        Purpose:
            Daily time series (rows: ``day``, ``transaction_count``,
            ``total_amount``), ascending by day.

        Parameters:
            start_date: First day (inclusive), or ``None``.
            end_date: Last day (inclusive), or ``None``.
            status: Outcome filter, or ``None``.

        Returns:
            One result row per day.
        """

        day = Transaction.transaction_date.label("day")
        return self._group_and_measure(
            day,
            start_date=start_date,
            end_date=end_date,
            status=status,
            order_by_group=True,
        )

    def group_by_month(
        self,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        status: str | None = None,
    ) -> Sequence[Row[Any]]:
        """Aggregate transactions per calendar month.

        Purpose:
            Monthly time series (rows: ``month`` — the first day of the
            month as a timestamp, ``transaction_count``, ``total_amount``),
            ascending by month. Truncation runs in PostgreSQL and derives
            from ``transaction_date`` — the same calendar column every date
            filter uses — so filters and grouping can never disagree.

        Parameters:
            start_date: First day (inclusive), or ``None``.
            end_date: Last day (inclusive), or ``None``.
            status: Outcome filter, or ``None``.

        Returns:
            One result row per month.
        """

        month = func.date_trunc("month", Transaction.transaction_date).label("month")
        return self._group_and_measure(
            month,
            start_date=start_date,
            end_date=end_date,
            status=status,
            order_by_group=True,
        )

    def group_by_bank(
        self,
        *,
        side: str = "payer",
        start_date: date | None = None,
        end_date: date | None = None,
        status: str | None = None,
        limit: int | None = None,
    ) -> Sequence[Row[Any]]:
        """Aggregate transactions per bank on one side.

        Purpose:
            Bank leaderboards (rows: ``bank``, ``transaction_count``,
            ``total_amount``), busiest bank first.

        Parameters:
            side: ``"payer"`` (debit side) or ``"payee"`` (credit side).
            start_date: First day (inclusive), or ``None``.
            end_date: Last day (inclusive), or ``None``.
            status: Outcome filter, or ``None``.
            limit: Keep only the top N groups (``None`` = all).

        Returns:
            One result row per bank.

        Raises:
            InvalidFilterError: For an unknown ``side``.
        """

        bank = self._bank_column(side).label("bank")
        return self._group_and_measure(
            bank,
            start_date=start_date,
            end_date=end_date,
            status=status,
            limit=limit,
        )

    def group_by_psp(
        self,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        status: str | None = None,
        limit: int | None = None,
    ) -> Sequence[Row[Any]]:
        """Aggregate transactions per payer-side PSP app.

        Purpose:
            PSP leaderboards (rows: ``psp``, ``transaction_count``,
            ``total_amount``), busiest PSP first.

        Parameters:
            start_date: First day (inclusive), or ``None``.
            end_date: Last day (inclusive), or ``None``.
            status: Outcome filter, or ``None``.
            limit: Keep only the top N groups (``None`` = all).

        Returns:
            One result row per PSP.
        """

        psp = Transaction.payer_psp.label("psp")
        return self._group_and_measure(
            psp,
            start_date=start_date,
            end_date=end_date,
            status=status,
            limit=limit,
        )

    def group_by_merchant(
        self,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        status: str | None = None,
        limit: int | None = None,
    ) -> Sequence[Row[Any]]:
        """Aggregate transactions per merchant (payee VPA + verified name).

        Purpose:
            Merchant leaderboards (rows: ``merchant_vpa``,
            ``merchant_name``, ``transaction_count``, ``total_amount``),
            busiest merchant first.

        Parameters:
            start_date: First day (inclusive), or ``None``.
            end_date: Last day (inclusive), or ``None``.
            status: Outcome filter, or ``None``.
            limit: Keep only the top N groups (``None`` = all).

        Returns:
            One result row per merchant.
        """

        return self._group_and_measure(
            Transaction.payee_vpa.label("merchant_vpa"),
            Transaction.payee_verified_name.label("merchant_name"),
            start_date=start_date,
            end_date=end_date,
            status=status,
            limit=limit,
        )

    def group_by_customer(
        self,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        status: str | None = None,
        limit: int | None = None,
    ) -> Sequence[Row[Any]]:
        """Aggregate transactions per customer (payer VPA).

        Purpose:
            Customer activity ranking (rows: ``customer_vpa``,
            ``transaction_count``, ``total_amount``), most active first.

        Parameters:
            start_date: First day (inclusive), or ``None``.
            end_date: Last day (inclusive), or ``None``.
            status: Outcome filter, or ``None``.
            limit: Keep only the top N groups (``None`` = all).

        Returns:
            One result row per customer.
        """

        customer = Transaction.payer_vpa.label("customer_vpa")
        return self._group_and_measure(
            customer,
            start_date=start_date,
            end_date=end_date,
            status=status,
            limit=limit,
        )

    # ------------------------------------------------------------------
    # Streaming access (constant-memory full scans)
    # ------------------------------------------------------------------
    def stream_transactions(
        self,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        status: str | None = None,
        batch_size: int = DEFAULT_STREAM_BATCH_SIZE,
    ) -> Iterator[Transaction]:
        """Iterate transactions lazily in server-side batches.

        Purpose:
            Constant-memory scans for future feature engineering or exports
            over 10M+ rows — rows are fetched ``batch_size`` at a time via
            ``yield_per`` instead of being materialized at once.

        Parameters:
            start_date: First day (inclusive), or ``None``.
            end_date: Last day (inclusive), or ``None``.
            status: Outcome filter, or ``None``.
            batch_size: Rows fetched per round trip.

        Returns:
            A lazy iterator of transactions, chronologically ordered.

        Raises:
            InvalidFilterError: For an invalid ``batch_size`` or date range.
        """

        if batch_size < 1:
            raise InvalidFilterError(f"batch_size must be >= 1, got {batch_size}")
        stmt = self._apply_transaction_filters(
            select(Transaction),
            start_date=start_date,
            end_date=end_date,
            status=status,
        ).order_by(Transaction.transaction_timestamp.asc())
        try:
            yield from self._session.scalars(
                stmt.execution_options(yield_per=batch_size)
            )
        except SQLAlchemyError as exc:
            raise self._wrap(exc, "streaming query") from exc

    # ------------------------------------------------------------------
    # Internal composable pieces
    # ------------------------------------------------------------------
    def _list(
        self,
        stmt: Select[Any],
        limit: int | None,
        offset: int,
        order_by: str,
        descending: bool,
    ) -> Sequence[Transaction]:
        """Shared ordering + pagination + execution path for listings."""

        stmt = self._apply_ordering(stmt, order_by, descending)
        stmt = self._apply_pagination(stmt, limit, offset)
        return self._execute_all(stmt)

    @staticmethod
    def _apply_transaction_filters(
        stmt: Select[Any],
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        status: str | None = None,
    ) -> Select[Any]:
        """Apply the shared optional period/outcome filters to a statement."""

        if start_date is not None and end_date is not None and start_date > end_date:
            raise InvalidFilterError(
                f"start_date {start_date} is after end_date {end_date}"
            )
        if start_date is not None:
            stmt = stmt.where(Transaction.transaction_date >= start_date)
        if end_date is not None:
            stmt = stmt.where(Transaction.transaction_date <= end_date)
        if status is not None:
            stmt = stmt.where(Transaction.status == status)
        return stmt

    def _group_and_measure(
        self,
        *group_expressions: Any,
        start_date: date | None,
        end_date: date | None,
        status: str | None,
        order_by_group: bool = False,
        limit: int | None = None,
    ) -> Sequence[Row[Any]]:
        """Shared grouping engine: count + total amount per group.

        Groups by the given labelled expressions; orders ascending by the
        first group expression (time series) or by count descending
        (leaderboards).
        """

        count_ = func.count().label("transaction_count")
        total = func.coalesce(
            func.sum(Transaction.transaction_amount), 0
        ).label("total_amount")
        stmt: Select[Any] = select(*group_expressions, count_, total)
        stmt = self._apply_transaction_filters(
            stmt, start_date=start_date, end_date=end_date, status=status
        ).group_by(*group_expressions)
        if order_by_group:
            stmt = stmt.order_by(group_expressions[0].asc())
        else:
            stmt = stmt.order_by(count_.desc())
        stmt = self._apply_pagination(stmt, limit, 0)
        return self._execute_rows(stmt)

    @staticmethod
    def _bank_column(side: str) -> InstrumentedAttribute[str]:
        """Resolve a transaction side to its bank-name column."""

        if side not in _SIDES:
            raise InvalidFilterError(
                f"side must be one of {_SIDES}, got {side!r}"
            )
        return Transaction.payer_bank if side == "payer" else Transaction.payee_bank
