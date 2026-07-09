"""Dashboard Service — DTO-ready data for future dashboards.

Purpose:
    Shape service-layer results into clean, presentation-agnostic
    dictionaries (cards, quick stats, activity feeds) that a future API
    layer can serialize directly. No charts, no HTML, no formatting — only
    structure.

Business notes:
    - Every figure is delegated to the KPI Service or the Transaction
      Service; this service owns *shape*, not *math*.
    - Card DTOs follow one schema: ``key``, ``title``, ``value``, ``unit``
      — so front-ends can render any card generically.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from app.repositories import (
    BankRepository,
    CustomerRepository,
    MerchantRepository,
    PspRepository,
)
from app.services.kpi_service import KpiService
from app.services.service_exceptions import translate_repository_errors
from app.services.transaction_service import TransactionService


def _card(key: str, title: str, value: Any, unit: str) -> dict[str, Any]:
    """Build one dashboard card DTO (single schema for every card)."""

    return {"key": key, "title": title, "value": value, "unit": unit}


class DashboardService:
    """DTO-ready dashboard data over the service layer.

    Parameters:
        kpi_service: Central KPI calculator.
        transaction_service: Transaction listings (recent activity).
        bank_repository: Bank master access (system overview).
        psp_repository: PSP master access (system overview).
        customer_repository: Customer master access (system overview).
        merchant_repository: Merchant master access (system overview).
    """

    def __init__(
        self,
        kpi_service: KpiService,
        transaction_service: TransactionService,
        bank_repository: BankRepository,
        psp_repository: PspRepository,
        customer_repository: CustomerRepository,
        merchant_repository: MerchantRepository,
    ) -> None:
        self._kpis = kpi_service
        self._transaction_service = transaction_service
        self._banks = bank_repository
        self._psps = psp_repository
        self._customers = customer_repository
        self._merchants = merchant_repository

    @translate_repository_errors
    def get_portfolio_cards(self) -> list[dict[str, Any]]:
        """Build the all-time portfolio KPI cards.

        Purpose:
            The headline card row of the future executive dashboard.

        Returns:
            Card DTOs: total transactions, total volume, average amount,
            success rate, unique customers, unique merchants.

        Business:
            One KPI snapshot feeds every card — figures on one dashboard
            can never disagree with each other.
        """

        kpis = self._kpis.get_kpi_snapshot()
        return [
            _card("total_transactions", "Total Transactions",
                  kpis["total_transactions"], "transactions"),
            _card("total_volume", "Total Volume",
                  kpis["total_volume"], "INR"),
            _card("average_transaction_amount", "Average Transaction Amount",
                  kpis["average_transaction_amount"], "INR"),
            _card("success_rate", "Success Rate",
                  kpis["success_rate"], "%"),
            _card("unique_customers", "Unique Customers",
                  kpis["unique_customers"], "customers"),
            _card("unique_merchants", "Unique Merchants",
                  kpis["unique_merchants"], "merchants"),
        ]

    @translate_repository_errors
    def get_summary_cards(
        self, *, start_date: date | None = None, end_date: date | None = None
    ) -> list[dict[str, Any]]:
        """Build the period summary cards.

        Purpose:
            The card row for period-scoped dashboard views.

        Parameters:
            start_date: First day (inclusive), or ``None`` for all time.
            end_date: Last day (inclusive), or ``None`` for all time.

        Returns:
            Card DTOs: transactions, successful, failed, volume, average
            amount, success rate for the period.

        Business:
            Uses the lighter KPI bundle (no participant grouping) so
            period switching stays fast.
        """

        kpis = self._kpis.get_transaction_kpis(
            start_date=start_date, end_date=end_date
        )
        return [
            _card("total_transactions", "Transactions",
                  kpis["total_transactions"], "transactions"),
            _card("successful_transactions", "Successful",
                  kpis["successful_transactions"], "transactions"),
            _card("failed_transactions", "Failed",
                  kpis["failed_transactions"], "transactions"),
            _card("total_volume", "Volume",
                  kpis["total_volume"], "INR"),
            _card("average_transaction_amount", "Average Amount",
                  kpis["average_transaction_amount"], "INR"),
            _card("success_rate", "Success Rate",
                  kpis["success_rate"], "%"),
        ]

    @translate_repository_errors
    def get_quick_stats(self) -> dict[str, Any]:
        """Build the compact all-time statistics block.

        Purpose:
            The small always-visible numbers strip of the dashboard.

        Returns:
            Dict with ``total_transactions``, ``total_volume``,
            ``success_rate``, ``approval_rate``.

        Business:
            Restricted to the four cheapest headline KPIs so it can be
            refreshed frequently.
        """

        kpis = self._kpis.get_transaction_kpis()
        return {
            "total_transactions": kpis["total_transactions"],
            "total_volume": kpis["total_volume"],
            "success_rate": kpis["success_rate"],
            "approval_rate": kpis["approval_rate"],
        }

    @translate_repository_errors
    def get_recent_activity(self, *, limit: int = 10) -> list[dict[str, Any]]:
        """Build the recent-activity feed.

        Purpose:
            The live transaction ticker of the dashboard.

        Parameters:
            limit: Number of transactions in the feed.

        Returns:
            Transaction summary DTOs, most recent first.

        Business:
            Delegated to the Transaction Service — one summary DTO shape
            platform-wide.
        """

        return self._transaction_service.get_recent_transactions(limit=limit)

    @translate_repository_errors
    def get_system_overview(self) -> dict[str, Any]:
        """Build the system/reference-data overview block.

        Purpose:
            The dashboard block describing what the platform contains.

        Returns:
            Dict with registered participant counts (``customers``,
            ``merchants``, ``banks``, ``psps``) and ``active_banks`` /
            ``active_psps``.

        Business:
            Master-level counts only — cheap enough to render on every
            dashboard load.
        """

        return {
            "customers": self._customers.count(),
            "merchants": self._merchants.count(),
            "banks": self._banks.count(),
            "psps": self._psps.count(),
            "active_banks": len(self._banks.find_active()),
            "active_psps": len(self._psps.find_active()),
        }
