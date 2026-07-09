"""Portfolio Service — executive-level views over the whole business.

Purpose:
    Roll the entire platform up into portfolio summaries: enterprise
    KPIs, participant counts, data coverage, and the business overview
    consumed by executive reporting.

Business notes:
    - All KPI figures are delegated to the KPI Service — this service
      adds composition (masters + coverage + top participants), never
      alternative math.
    - "Registered" figures come from the masters; "active" figures come
      from the fact via the KPI Service. Both are reported side by side
      because executives ask for both.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from app.repositories import (
    BankRepository,
    CustomerRepository,
    MerchantRepository,
    PspRepository,
    TransactionRepository,
)
from app.services.kpi_service import KpiService, money
from app.services.service_exceptions import translate_repository_errors


class PortfolioService:
    """Executive portfolio summaries over the whole platform.

    Parameters:
        kpi_service: Central KPI calculator.
        transaction_repository: Fact-table access (coverage, top groups).
        bank_repository: Bank master access.
        psp_repository: PSP master access.
        customer_repository: Customer master access.
        merchant_repository: Merchant master access.
    """

    def __init__(
        self,
        kpi_service: KpiService,
        transaction_repository: TransactionRepository,
        bank_repository: BankRepository,
        psp_repository: PspRepository,
        customer_repository: CustomerRepository,
        merchant_repository: MerchantRepository,
    ) -> None:
        self._kpis = kpi_service
        self._transactions = transaction_repository
        self._banks = bank_repository
        self._psps = psp_repository
        self._customers = customer_repository
        self._merchants = merchant_repository

    @translate_repository_errors
    def get_portfolio_summary(self) -> dict[str, Any]:
        """Compute the all-time portfolio summary.

        Purpose:
            The single executive answer to "how big is this business?".

        Returns:
            Dict with ``kpis`` (full snapshot), ``participants``
            (registered master counts), and ``coverage``
            (``first_transaction_date``, ``last_transaction_date``,
            ``days_with_activity``).

        Business:
            Registered participants (master counts) are reported next to
            active participants (inside the KPI snapshot) — growth teams
            track the gap between the two.
        """

        daily = self._transactions.group_by_day()
        return {
            "kpis": self._kpis.get_kpi_snapshot(),
            "participants": {
                "registered_customers": self._customers.count(),
                "registered_merchants": self._merchants.count(),
                "member_banks": self._banks.count(),
                "member_psps": self._psps.count(),
            },
            "coverage": {
                "first_transaction_date": daily[0].day if daily else None,
                "last_transaction_date": daily[-1].day if daily else None,
                "days_with_activity": len(daily),
            },
        }

    @translate_repository_errors
    def get_business_overview(self, *, top_n: int = 5) -> dict[str, Any]:
        """Compute the executive business overview.

        Purpose:
            The portfolio summary extended with the leading participants —
            the standard opening view of executive reporting.

        Parameters:
            top_n: How many leading banks/PSPs/merchants to include.

        Returns:
            Dict with ``summary`` (per :meth:`get_portfolio_summary`) and
            ``leaders`` (``top_banks``, ``top_psps``, ``top_merchants`` —
            each a list of name/count/amount dicts, busiest first).

        Business:
            "Leaders by traffic" is descriptive composition, not ranking
            analytics — scoring and movement analysis arrive in Phase 8.
        """

        return {
            "summary": self.get_portfolio_summary(),
            "leaders": {
                "top_banks": [
                    {
                        "name": row.bank,
                        "transaction_count": row.transaction_count,
                        "total_amount": money(row.total_amount),
                    }
                    for row in self._transactions.group_by_bank(limit=top_n)
                ],
                "top_psps": [
                    {
                        "name": row.psp,
                        "transaction_count": row.transaction_count,
                        "total_amount": money(row.total_amount),
                    }
                    for row in self._transactions.group_by_psp(limit=top_n)
                ],
                "top_merchants": [
                    {
                        "name": row.merchant_name,
                        "vpa": row.merchant_vpa,
                        "transaction_count": row.transaction_count,
                        "total_amount": money(row.total_amount),
                    }
                    for row in self._transactions.group_by_merchant(limit=top_n)
                ],
            },
        }

    @translate_repository_errors
    def get_transaction_summary(
        self, *, start_date: date | None = None, end_date: date | None = None
    ) -> dict[str, Any]:
        """Compute the portfolio transaction scorecard for a period.

        Purpose:
            Period-bounded executive scorecard (month/quarter reviews).

        Parameters:
            start_date: First day (inclusive), or ``None`` for all time.
            end_date: Last day (inclusive), or ``None`` for all time.

        Returns:
            The canonical KPI bundle for the period.

        Business:
            Delegated verbatim to the KPI Service — one source of truth.
        """

        return self._kpis.get_transaction_kpis(
            start_date=start_date, end_date=end_date
        )
