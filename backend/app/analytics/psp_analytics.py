"""PSP Analytics — rankings, performance, contribution, and trends.

Purpose:
    Transform the PSP traffic table (PSP Service) into analytical insight:
    which payment-service providers carry the platform, how they perform,
    how their traffic concentrates, and how a provider moves over time.

Business notes:
    - Every analysis derives from ``PspService.get_psp_overview`` — one
      authoritative per-PSP table (payer-side by schema design, busiest
      first). Per-PSP figures, including success rate, are owned by the
      service.
    - PSP traffic rows carry ``psp``, ``total_transactions``,
      ``successful_transactions``, ``success_rate``, and ``total_amount``.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from app.analytics.analytics_exceptions import (
    InvalidAnalysisRequestError,
    translate_service_errors,
)
from app.analytics.analytics_utils import (
    contribution_table,
    describe_distribution,
    month_windows,
    percent_change,
    rank_rows,
)
from app.services import PspService


class PspAnalytics:
    """Analytical views over PSP traffic.

    Parameters:
        psp_service: Business-level PSP access.
    """

    def __init__(self, psp_service: PspService) -> None:
        self._psps = psp_service

    @translate_service_errors
    def get_psp_rankings(
        self,
        *,
        by: str = "total_transactions",
        descending: bool = True,
        top_n: int | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[dict[str, Any]]:
        """Rank PSPs by a traffic metric.

        Purpose:
            The general PSP leaderboard.

        Business Meaning:
            Which providers carry the platform on the chosen metric —
            count, volume, or reliability.

        Parameters:
            by: Metric key (``total_transactions``, ``total_amount``,
                ``successful_transactions``, ``success_rate``).
            descending: ``True`` ranks highest-first.
            top_n: Keep only the first N (``None`` = all PSPs).
            start_date: First day (inclusive), or ``None`` for all time.
            end_date: Last day (inclusive), or ``None`` for all time.

        Returns:
            Ranked PSP traffic rows (each with ``rank``).
        """

        rows = self._psps.get_psp_overview(start_date=start_date, end_date=end_date)
        return rank_rows(rows, by=by, descending=descending, top_n=top_n)

    @translate_service_errors
    def get_top_psps(
        self,
        *,
        n: int = 5,
        by: str = "total_transactions",
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[dict[str, Any]]:
        """The N leading PSPs on a metric.

        Purpose:
            The head of the PSP leaderboard.

        Business Meaning:
            The platform's anchor providers.

        Parameters:
            n: How many PSPs.
            by: Metric key (see :meth:`get_psp_rankings`).
            start_date: First day (inclusive), or ``None`` for all time.
            end_date: Last day (inclusive), or ``None`` for all time.

        Returns:
            Ranked rows, best first.
        """

        return self.get_psp_rankings(
            by=by, descending=True, top_n=n,
            start_date=start_date, end_date=end_date,
        )

    @translate_service_errors
    def get_psp_performance(
        self, *, start_date: date | None = None, end_date: date | None = None
    ) -> dict[str, Any]:
        """Performance profile across all PSPs.

        Purpose:
            The at-a-glance state of the provider base.

        Business Meaning:
            The full provider table with the spread of activity, volume,
            and reliability — the context for every PSP decision.

        Parameters:
            start_date: First day (inclusive), or ``None`` for all time.
            end_date: Last day (inclusive), or ``None`` for all time.

        Returns:
            Dict with ``active_psps``, ``psps`` (full traffic table ranked
            by transaction count), and ``transaction_count_stats`` /
            ``success_rate_stats`` (descriptive statistics across PSPs).
        """

        rows = self._psps.get_psp_overview(start_date=start_date, end_date=end_date)
        return {
            "active_psps": len(rows),
            "psps": rank_rows(rows, by="total_transactions"),
            "transaction_count_stats": describe_distribution(
                [row["total_transactions"] for row in rows]
            ),
            "success_rate_stats": describe_distribution(
                [row["success_rate"] for row in rows]
            ),
        }

    @translate_service_errors
    def get_psp_contribution(
        self,
        *,
        top_n: int = 5,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> dict[str, Any]:
        """PSP contribution and concentration analysis.

        Purpose:
            How PSP traffic concentrates across providers.

        Business Meaning:
            Reliance risk: how much of platform volume the leading
            providers represent.

        Parameters:
            top_n: How many leading PSPs to detail.
            start_date: First day (inclusive), or ``None`` for all time.
            end_date: Last day (inclusive), or ``None`` for all time.

        Returns:
            The standard contribution object (see
            :func:`analytics_utils.contribution_table`): ``total_transactions``,
            ``total_amount``, ``leaders`` (with count/amount/cumulative
            shares), and the combined ``top_n`` shares.
        """

        rows = self._psps.get_psp_overview(start_date=start_date, end_date=end_date)
        return contribution_table(
            rows,
            count_field="total_transactions",
            amount_field="total_amount",
            label_field="psp",
            top_n=top_n,
        )

    @translate_service_errors
    def get_success_analysis(
        self,
        *,
        minimum_transactions: int = 100,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> dict[str, Any]:
        """PSP payment-success analysis.

        Purpose:
            Reliability seen provider by provider.

        Business Meaning:
            Which providers experience the worst payment success — the
            factual input for provider remediation.

        Parameters:
            minimum_transactions: Ignore PSPs below this activity (tiny
                samples make ratios meaningless).
            start_date: First day (inclusive), or ``None`` for all time.
            end_date: Last day (inclusive), or ``None`` for all time.

        Returns:
            Dict with ``qualifying_psps``, ``minimum_transactions``,
            ``success_rate_stats`` (descriptive statistics), and
            ``worst`` / ``best`` (ranked by success rate).

        Raises:
            InvalidAnalysisRequestError: For a negative threshold.
        """

        if minimum_transactions < 0:
            raise InvalidAnalysisRequestError(
                f"minimum_transactions must be >= 0, got {minimum_transactions}"
            )
        rows = [
            row
            for row in self._psps.get_psp_overview(
                start_date=start_date, end_date=end_date
            )
            if row["total_transactions"] >= minimum_transactions
        ]
        return {
            "qualifying_psps": len(rows),
            "minimum_transactions": minimum_transactions,
            "success_rate_stats": describe_distribution(
                [row["success_rate"] for row in rows]
            ),
            "worst": rank_rows(rows, by="success_rate", descending=False),
            "best": rank_rows(rows, by="success_rate", descending=True),
        }

    @translate_service_errors
    def get_psp_trend(
        self, psp_name: str, start_date: date, end_date: date
    ) -> dict[str, Any]:
        """Monthly traffic trend for one PSP.

        Purpose:
            The movement view of a single provider.

        Business Meaning:
            Month by month, how one provider's activity, volume, and
            reliability move — the factual basis for a provider review.

        Parameters:
            psp_name: PSP display name (as carried on the fact).
            start_date: First day of the range (inclusive).
            end_date: Last day of the range (inclusive).

        Returns:
            Trend object: ``psp``, ``grain`` (``monthly``), and ``series``
            rows with ``period`` (month start), ``transaction_count``,
            ``successful_transactions``, ``success_rate``, ``total_amount``,
            and ``count_change_pct`` (``None`` for the first month).
            Months with no traffic for the PSP carry zeros.

        Raises:
            InvalidAnalysisRequestError: If the range is inverted.
        """

        series: list[dict[str, Any]] = []
        previous: dict[str, Any] | None = None
        for window_start, window_end in month_windows(start_date, end_date):
            row = next(
                (
                    entry
                    for entry in self._psps.get_psp_overview(
                        start_date=window_start, end_date=window_end
                    )
                    if entry["psp"] == psp_name
                ),
                None,
            )
            count = row["total_transactions"] if row else 0
            entry = {
                "period": window_start,
                "transaction_count": count,
                "successful_transactions": (
                    row["successful_transactions"] if row else 0
                ),
                "success_rate": row["success_rate"] if row else 0.0,
                "total_amount": row["total_amount"] if row else Decimal("0.00"),
                "count_change_pct": (
                    percent_change(count, previous["transaction_count"])
                    if previous
                    else None
                ),
            }
            series.append(entry)
            previous = entry
        return {"psp": psp_name, "grain": "monthly", "series": series}
