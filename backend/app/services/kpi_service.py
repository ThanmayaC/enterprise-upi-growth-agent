"""KPI Service — the single source of truth for enterprise KPI math.

Purpose:
    Centralize every KPI definition so Analytics (Phase 8), Reports, and
    the AI Assistant all cite identical numbers. No other service computes
    a KPI; they inject this service and delegate.

Business definitions (frozen here, verified against the dataset):
    - Total Transactions   — every network event in the period, financial
      and non-financial (mandate lifecycle) alike.
    - Total Volume         — the money that actually moved: the sum of
      transaction amounts over SUCCESSFUL transactions only.
    - Average Transaction Amount — Total Volume ÷ successful transactions.
      Successful mandate-lifecycle operations carry no amount, so this is
      a conservative per-transaction average (≈2.7% below the pure
      financial-ticket average on the current dataset). A financial-only
      denominator awaits a category-aware count in the Phase 8 repository
      extension.
    - Success / Failure Rate — share of all transactions with that
      terminal outcome.
    - Approval Rate        — SUCCESS ÷ (SUCCESS + FAILURE). Identical to
      the success rate while the network reports only two terminal states,
      but robust if pending/deemed states appear in future data.
    - Unique Customers     — distinct payer VPAs active in the period.
    - Unique Merchants     — distinct payee VPAs active in the period that
      exist in the merchant master (person payees are excluded).
"""

from __future__ import annotations

from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from app.repositories import MerchantRepository, TransactionRepository
from app.services.service_exceptions import translate_repository_errors

#: Terminal outcome literals as stored on the fact (``responseresult``).
STATUS_SUCCESS = "SUCCESS"
STATUS_FAILURE = "FAILURE"

_TWO_PLACES = Decimal("0.01")


def percentage(part: int, whole: int) -> float:
    """Compute a share as a percentage, guarded against empty denominators.

    Purpose:
        One rounding/zero-guard convention for every rate the platform
        reports.

    Parameters:
        part: Numerator count.
        whole: Denominator count.

    Returns:
        ``part / whole`` as a percentage rounded to 2 decimals; ``0.0``
        when the denominator is zero.
    """

    if whole <= 0:
        return 0.0
    return round(part * 100 / whole, 2)


def money(amount: Decimal) -> Decimal:
    """Quantize a monetary value to 2 decimal places (banker-safe).

    Purpose:
        One monetary rounding convention (half-up, paisa precision) for
        every amount the platform reports.

    Parameters:
        amount: The exact amount.

    Returns:
        The amount quantized to 0.01.
    """

    return amount.quantize(_TWO_PLACES, rounding=ROUND_HALF_UP)


class KpiService:
    """Enterprise KPI calculations over the transaction fact.

    Parameters:
        transaction_repository: Fact-table access.
        merchant_repository: Merchant master access (used to separate
            merchant payees from person payees).
    """

    def __init__(
        self,
        transaction_repository: TransactionRepository,
        merchant_repository: MerchantRepository,
    ) -> None:
        self._transactions = transaction_repository
        self._merchants = merchant_repository

    # ------------------------------------------------------------------
    # Individual KPIs
    # ------------------------------------------------------------------
    @translate_repository_errors
    def get_total_transactions(
        self, *, start_date: date | None = None, end_date: date | None = None
    ) -> int:
        """Total Transactions KPI.

        Purpose:
            Headline activity metric for a period.

        Parameters:
            start_date: First day (inclusive), or ``None`` for all time.
            end_date: Last day (inclusive), or ``None`` for all time.

        Returns:
            The number of transactions in the period.

        Business:
            Counts every network event — financial payments and mandate
            lifecycle operations alike — because each represents customer
            activity on the platform.
        """

        return self._transactions.count_transactions(
            start_date=start_date, end_date=end_date
        )

    @translate_repository_errors
    def get_total_volume(
        self, *, start_date: date | None = None, end_date: date | None = None
    ) -> Decimal:
        """Total Volume KPI.

        Purpose:
            Headline money-movement metric for a period.

        Parameters:
            start_date: First day (inclusive), or ``None`` for all time.
            end_date: Last day (inclusive), or ``None`` for all time.

        Returns:
            The summed amount of successful transactions, in exact
            ``Decimal`` rupees.

        Business:
            Only successful transactions moved money; failed attempts are
            excluded by definition.
        """

        return money(
            self._transactions.sum_transaction_amount(
                start_date=start_date, end_date=end_date, status=STATUS_SUCCESS
            )
        )

    @translate_repository_errors
    def get_average_transaction_amount(
        self, *, start_date: date | None = None, end_date: date | None = None
    ) -> Decimal:
        """Average Transaction Amount KPI.

        Purpose:
            Ticket-size indicator for a period.

        Parameters:
            start_date: First day (inclusive), or ``None`` for all time.
            end_date: Last day (inclusive), or ``None`` for all time.

        Returns:
            Total Volume divided by successful transactions (``0`` when
            the period has none), quantized to 2 decimals.

        Business:
            See the module docstring: the denominator includes successful
            non-financial mandate operations, making this a conservative
            average.
        """

        successes = self._transactions.count_transactions(
            start_date=start_date, end_date=end_date, status=STATUS_SUCCESS
        )
        if successes == 0:
            return Decimal("0.00")
        volume = self._transactions.sum_transaction_amount(
            start_date=start_date, end_date=end_date, status=STATUS_SUCCESS
        )
        return money(volume / successes)

    @translate_repository_errors
    def get_success_rate(
        self, *, start_date: date | None = None, end_date: date | None = None
    ) -> float:
        """Success Rate KPI (percentage of all transactions).

        Purpose:
            The platform's most-watched reliability metric.

        Parameters:
            start_date: First day (inclusive), or ``None`` for all time.
            end_date: Last day (inclusive), or ``None`` for all time.

        Returns:
            Successful share of all transactions, in percent (2 decimals).

        Business:
            Denominator is all transactions in the period, so this and the
            failure rate decompose the whole book.
        """

        return percentage(
            self._transactions.count_transactions(
                start_date=start_date, end_date=end_date, status=STATUS_SUCCESS
            ),
            self._transactions.count_transactions(
                start_date=start_date, end_date=end_date
            ),
        )

    @translate_repository_errors
    def get_failure_rate(
        self, *, start_date: date | None = None, end_date: date | None = None
    ) -> float:
        """Failure Rate KPI (percentage of all transactions).

        Purpose:
            Reliability counterpart of the success rate.

        Parameters:
            start_date: First day (inclusive), or ``None`` for all time.
            end_date: Last day (inclusive), or ``None`` for all time.

        Returns:
            Failed share of all transactions, in percent (2 decimals).

        Business:
            Feeds failure decomposition and error-Pareto analytics in
            Phase 8.
        """

        return percentage(
            self._transactions.count_transactions(
                start_date=start_date, end_date=end_date, status=STATUS_FAILURE
            ),
            self._transactions.count_transactions(
                start_date=start_date, end_date=end_date
            ),
        )

    @translate_repository_errors
    def get_approval_rate(
        self, *, start_date: date | None = None, end_date: date | None = None
    ) -> float:
        """Approval Rate KPI (percentage of decided transactions).

        Purpose:
            Outcome quality over transactions that reached a terminal
            approve/decline decision.

        Parameters:
            start_date: First day (inclusive), or ``None`` for all time.
            end_date: Last day (inclusive), or ``None`` for all time.

        Returns:
            SUCCESS ÷ (SUCCESS + FAILURE) in percent (2 decimals).

        Business:
            Equals the success rate while only two terminal states exist;
            diverges (by design) if pending/deemed states appear later.
        """

        successes = self._transactions.count_transactions(
            start_date=start_date, end_date=end_date, status=STATUS_SUCCESS
        )
        failures = self._transactions.count_transactions(
            start_date=start_date, end_date=end_date, status=STATUS_FAILURE
        )
        return percentage(successes, successes + failures)

    @translate_repository_errors
    def get_unique_customers(
        self, *, start_date: date | None = None, end_date: date | None = None
    ) -> int:
        """Unique Customers KPI.

        Purpose:
            Breadth of customer activity in a period.

        Parameters:
            start_date: First day (inclusive), or ``None`` for all time.
            end_date: Last day (inclusive), or ``None`` for all time.

        Returns:
            The number of distinct payer VPAs active in the period.

        Business:
            The payer is always the customer in the frozen schema, so
            distinct payer VPAs measure the active customer base.
        """

        return len(
            self._transactions.group_by_customer(
                start_date=start_date, end_date=end_date
            )
        )

    @translate_repository_errors
    def get_unique_merchants(
        self, *, start_date: date | None = None, end_date: date | None = None
    ) -> int:
        """Unique Merchants KPI.

        Purpose:
            Breadth of merchant activity in a period.

        Parameters:
            start_date: First day (inclusive), or ``None`` for all time.
            end_date: Last day (inclusive), or ``None`` for all time.

        Returns:
            The number of distinct merchant payees active in the period.

        Business:
            Payees include persons (P2P); only payees present in the
            merchant master count as merchants here.
        """

        merchant_vpas = {m.payee_vpa for m in self._merchants.find_all()}
        active_payees = self._transactions.group_by_merchant(
            start_date=start_date, end_date=end_date
        )
        return sum(1 for row in active_payees if row.merchant_vpa in merchant_vpas)

    # ------------------------------------------------------------------
    # Bundles (shared cores — each underlying count computed exactly once)
    # ------------------------------------------------------------------
    @translate_repository_errors
    def get_transaction_kpis(
        self, *, start_date: date | None = None, end_date: date | None = None
    ) -> dict[str, Any]:
        """Volume-and-outcome KPI bundle for a period.

        Purpose:
            The shared core consumed by transaction summaries, portfolio
            views, and dashboards — four repository calls, every derived
            figure computed from them exactly once.

        Parameters:
            start_date: First day (inclusive), or ``None`` for all time.
            end_date: Last day (inclusive), or ``None`` for all time.

        Returns:
            Dict with ``total_transactions``, ``successful_transactions``,
            ``failed_transactions``, ``total_volume``,
            ``average_transaction_amount``, ``success_rate``,
            ``failure_rate``, ``approval_rate``.

        Business:
            Definitions per the module docstring; this bundle is the
            canonical period scorecard.
        """

        total = self._transactions.count_transactions(
            start_date=start_date, end_date=end_date
        )
        successes = self._transactions.count_transactions(
            start_date=start_date, end_date=end_date, status=STATUS_SUCCESS
        )
        failures = self._transactions.count_transactions(
            start_date=start_date, end_date=end_date, status=STATUS_FAILURE
        )
        volume = self._transactions.sum_transaction_amount(
            start_date=start_date, end_date=end_date, status=STATUS_SUCCESS
        )
        return {
            "total_transactions": total,
            "successful_transactions": successes,
            "failed_transactions": failures,
            "total_volume": money(volume),
            "average_transaction_amount": (
                money(volume / successes) if successes else Decimal("0.00")
            ),
            "success_rate": percentage(successes, total),
            "failure_rate": percentage(failures, total),
            "approval_rate": percentage(successes, successes + failures),
        }

    @translate_repository_errors
    def get_kpi_snapshot(
        self, *, start_date: date | None = None, end_date: date | None = None
    ) -> dict[str, Any]:
        """Complete enterprise KPI snapshot for a period.

        Purpose:
            Everything :meth:`get_transaction_kpis` reports, plus the
            unique-participant KPIs — the full executive scorecard.

        Parameters:
            start_date: First day (inclusive), or ``None`` for all time.
            end_date: Last day (inclusive), or ``None`` for all time.

        Returns:
            The :meth:`get_transaction_kpis` dict extended with
            ``unique_customers`` and ``unique_merchants``.

        Business:
            The participant KPIs require full-fact grouping and are the
            snapshot's most expensive components; callers that don't need
            them should prefer :meth:`get_transaction_kpis`.
        """

        snapshot = self.get_transaction_kpis(
            start_date=start_date, end_date=end_date
        )
        snapshot["unique_customers"] = self.get_unique_customers(
            start_date=start_date, end_date=end_date
        )
        snapshot["unique_merchants"] = self.get_unique_merchants(
            start_date=start_date, end_date=end_date
        )
        return snapshot
