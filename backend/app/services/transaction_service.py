"""Transaction Service — business-level access to individual transactions.

Purpose:
    Retrieval, filtering, and summary views over the transaction fact, in
    DTO form: ORM entities never leave the service layer, so higher layers
    (Analytics, APIs, AI Assistant) stay persistence-agnostic.

Business notes:
    - KPI math is delegated to the injected :class:`KpiService` — this
      service never re-implements a KPI.
    - Two DTO shapes: the *summary* (list rows, recent-activity feeds) and
      the *detail* (single-transaction views incl. mandate lifecycle
      fields). Both are plain dictionaries.
"""

from __future__ import annotations

import itertools
from datetime import date
from typing import Any

from app.models import Transaction
from app.repositories import TransactionRepository
from app.services.kpi_service import KpiService
from app.services.service_exceptions import (
    DataNotFoundError,
    ValidationError,
    require_non_empty,
    translate_repository_errors,
)


def transaction_to_summary(txn: Transaction) -> dict[str, Any]:
    """Convert one transaction entity to its summary DTO.

    Purpose:
        The shared list-row shape used across services and dashboards.

    Parameters:
        txn: The ORM entity.

    Returns:
        Dict with the identity, timing, parties, amount, and outcome of
        the transaction.
    """

    return {
        "transaction_id": txn.transaction_id,
        "timestamp": txn.transaction_timestamp,
        "date": txn.transaction_date,
        "type": txn.transaction_type,
        "category": txn.transaction_category,
        "amount": txn.transaction_amount,
        "status": txn.status,
        "payer_vpa": txn.payer_vpa,
        "payer_bank": txn.payer_bank,
        "payer_psp": txn.payer_psp,
        "payee_vpa": txn.payee_vpa,
        "payee_name": txn.payee_verified_name,
        "payee_bank": txn.payee_bank,
        "mcc_code": txn.mcc_code,
        "error_code": txn.error_code,
    }


def transaction_to_details(txn: Transaction) -> dict[str, Any]:
    """Convert one transaction entity to its detail DTO.

    Purpose:
        The single-transaction view: the summary plus purpose, credential,
        response, and mandate-lifecycle context.

    Parameters:
        txn: The ORM entity.

    Returns:
        The summary dict extended with detail fields.
    """

    details = transaction_to_summary(txn)
    details.update(
        {
            "customer_reference_number": txn.customer_reference_number,
            "purpose": txn.purpose,
            "purpose_code": txn.purpose_code,
            "initiation_mode": txn.initiation_mode,
            "initiated_by": txn.initiated_by,
            "credential_type": txn.credential_type,
            "response_code": txn.response_code,
            "status_description": txn.current_status_description,
            "payee_amount": txn.payee_amount,
            "unique_mandate_number": txn.unique_mandate_number,
            "mandate_operation": txn.mandate_operation,
            "recurrence_pattern": txn.recurrence_pattern,
            "as_of_timestamp": txn.as_of_timestamp,
        }
    )
    return details


class TransactionService:
    """Business-level transaction retrieval and summaries.

    Parameters:
        transaction_repository: Fact-table access.
        kpi_service: Central KPI calculator (volume/amount summaries).
    """

    def __init__(
        self,
        transaction_repository: TransactionRepository,
        kpi_service: KpiService,
    ) -> None:
        self._transactions = transaction_repository
        self._kpis = kpi_service

    @translate_repository_errors
    def get_transaction_details(self, transaction_id: str) -> dict[str, Any]:
        """Fetch the full business view of one transaction.

        Purpose:
            Dispute/support and detail-screen lookups.

        Parameters:
            transaction_id: The UPI network transaction id.

        Returns:
            The detail DTO.

        Business:
            A missing transaction is an error at this level — callers ask
            for a specific id and must learn decisively that it is unknown.

        Raises:
            DataNotFoundError: If the id is unknown.
            ValidationError: If the id is blank.
        """

        transaction_id = require_non_empty(transaction_id, "transaction_id")
        txn = self._transactions.get_transaction_by_id(transaction_id)
        if txn is None:
            raise DataNotFoundError(f"transaction '{transaction_id}' does not exist")
        return transaction_to_details(txn)

    @translate_repository_errors
    def list_transactions(
        self,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """List transactions as summary DTOs with business filters.

        Purpose:
            The general paged listing behind transaction browsers.

        Parameters:
            start_date: First day (inclusive), or ``None``.
            end_date: Last day (inclusive), or ``None``.
            status: Terminal outcome filter, or ``None``.
            limit: Page size.
            offset: Rows to skip.

        Returns:
            One page of summary DTOs. Unfiltered and status-only pages are
            most-recent-first; period pages are chronological (reading a
            period forward).

        Business:
            Combines the period and outcome filters callers use most.
            Period pages are served from the repository's server-side
            stream, so only the requested page is ever materialized.

        Raises:
            ValidationError: For negative ``limit``/``offset``.
        """

        if limit < 0 or offset < 0:
            raise ValidationError(
                f"limit and offset must be >= 0, got limit={limit} offset={offset}"
            )
        if start_date is None and end_date is None:
            if status is not None:
                rows: list[Transaction] = list(
                    self._transactions.get_transactions_by_status(
                        status, limit=limit, offset=offset
                    )
                )
            else:
                rows = list(
                    self._transactions.get_transactions(
                        limit=limit, offset=offset, descending=True
                    )
                )
        else:
            stream = self._transactions.stream_transactions(
                start_date=start_date, end_date=end_date, status=status
            )
            rows = list(itertools.islice(stream, offset, offset + limit))
        return [transaction_to_summary(txn) for txn in rows]

    @translate_repository_errors
    def get_recent_transactions(self, *, limit: int = 10) -> list[dict[str, Any]]:
        """List the most recent transactions.

        Purpose:
            Recent-activity feeds for dashboards and operations views.

        Parameters:
            limit: Number of transactions to return.

        Returns:
            Summary DTOs, most recent first.

        Business:
            Recency is by event timestamp — what an operator means by
            "just happened".
        """

        rows = self._transactions.get_transactions(
            limit=limit, offset=0, order_by="transaction_timestamp", descending=True
        )
        return [transaction_to_summary(txn) for txn in rows]

    @translate_repository_errors
    def get_volume_summary(
        self, *, start_date: date | None = None, end_date: date | None = None
    ) -> dict[str, Any]:
        """Volume and outcome summary for a period.

        Purpose:
            The period scorecard behind transaction-level reporting.

        Parameters:
            start_date: First day (inclusive), or ``None`` for all time.
            end_date: Last day (inclusive), or ``None`` for all time.

        Returns:
            The canonical KPI bundle (counts, volume, average, rates).

        Business:
            Delegated verbatim to the KPI Service so every layer reports
            identical numbers.
        """

        return self._kpis.get_transaction_kpis(
            start_date=start_date, end_date=end_date
        )

    @translate_repository_errors
    def get_daily_volume(
        self,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        """Daily transaction counts and amounts for a period.

        Purpose:
            The day-level time series behind trend views.

        Parameters:
            start_date: First day (inclusive), or ``None``.
            end_date: Last day (inclusive), or ``None``.
            status: Terminal outcome filter, or ``None``.

        Returns:
            Chronological dicts: ``day``, ``transaction_count``,
            ``total_amount``.

        Business:
            Aggregation happens in the database; this method only shapes
            rows into DTOs.
        """

        rows = self._transactions.group_by_day(
            start_date=start_date, end_date=end_date, status=status
        )
        return [
            {
                "day": row.day,
                "transaction_count": row.transaction_count,
                "total_amount": row.total_amount,
            }
            for row in rows
        ]

    @translate_repository_errors
    def get_monthly_volume(
        self,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        """Monthly transaction counts and amounts for a period.

        Purpose:
            The month-level time series behind trend views.

        Parameters:
            start_date: First day (inclusive), or ``None``.
            end_date: Last day (inclusive), or ``None``.
            status: Terminal outcome filter, or ``None``.

        Returns:
            Chronological dicts: ``month`` (first day of month),
            ``transaction_count``, ``total_amount``.

        Business:
            Months derive from the same calendar column as every filter,
            so series and scorecards always reconcile.
        """

        rows = self._transactions.group_by_month(
            start_date=start_date, end_date=end_date, status=status
        )
        return [
            {
                "month": row.month.date() if hasattr(row.month, "date") else row.month,
                "transaction_count": row.transaction_count,
                "total_amount": row.total_amount,
            }
            for row in rows
        ]
