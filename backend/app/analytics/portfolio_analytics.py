"""Portfolio Analytics — executive insight over the whole platform.

Purpose:
    Transform the service layer's portfolio and KPI outputs into
    executive analytics: snapshots, growth overviews, health indicators,
    trends, and period comparisons.

Business notes:
    - Every KPI figure originates in the KPI Service; this module derives
      *movement* and *comparison* on top, never alternative KPI math.
    - Deterministic and descriptive: indicators are reported with their
      changes, without invented health thresholds — judgment belongs to
      the consumers (Reports, AI Assistant).
"""

from __future__ import annotations

from datetime import date
from typing import Any

from app.analytics.analytics_exceptions import translate_service_errors
from app.analytics.analytics_utils import percent_change
from app.analytics.time_analytics import TimeAnalytics
from app.services import KpiService, PortfolioService
from app.services.kpi_service import STATUS_SUCCESS, percentage


class PortfolioAnalytics:
    """Executive portfolio insights.

    Parameters:
        portfolio_service: Executive composition service.
        kpi_service: Central KPI calculator.
        time_analytics: Time-series engine (monthly trends).
    """

    def __init__(
        self,
        portfolio_service: PortfolioService,
        kpi_service: KpiService,
        time_analytics: TimeAnalytics,
    ) -> None:
        self._portfolio = portfolio_service
        self._kpis = kpi_service
        self._time = time_analytics

    @translate_service_errors
    def get_executive_snapshot(self, *, top_n: int = 5) -> dict[str, Any]:
        """The complete executive snapshot of the platform.

        Purpose:
            One call answering "where does the business stand today?".

        Business Meaning:
            Headline KPIs, participant base, data coverage, and the
            leading banks/PSPs/merchants — the opening page of any
            executive review.

        Parameters:
            top_n: How many leaders per category to include.

        Returns:
            Dict with ``kpis``, ``participants``, ``coverage``, and
            ``leaders`` (top banks/PSPs/merchants).
        """

        overview = self._portfolio.get_business_overview(top_n=top_n)
        summary = overview["summary"]
        return {
            "kpis": summary["kpis"],
            "participants": summary["participants"],
            "coverage": summary["coverage"],
            "leaders": overview["leaders"],
        }

    @translate_service_errors
    def get_portfolio_trend(
        self, *, start_date: date | None = None, end_date: date | None = None
    ) -> dict[str, Any]:
        """Monthly portfolio performance trend.

        Purpose:
            The portfolio's canonical movement view.

        Business Meaning:
            Month-by-month activity, volume, and reliability in one
            series: each month carries counts, successful counts, volume,
            success rate, and month-over-month changes.

        Parameters:
            start_date: First day (inclusive), or ``None``.
            end_date: Last day (inclusive), or ``None``.

        Returns:
            Trend object: ``series`` rows with ``period``,
            ``transaction_count``, ``successful_count``, ``total_amount``,
            ``success_rate``, ``count_change_pct``, ``amount_change_pct``;
            plus the standard ``summary``.
        """

        all_trend = self._time.get_monthly_trend(
            start_date=start_date, end_date=end_date
        )
        success_by_month = {
            row["period"]: row
            for row in self._time.get_monthly_trend(
                start_date=start_date, end_date=end_date, status=STATUS_SUCCESS
            )["series"]
        }
        series = []
        for row in all_trend["series"]:
            succeeded = success_by_month.get(row["period"])
            success_count = succeeded["transaction_count"] if succeeded else 0
            series.append(
                {
                    **row,
                    "successful_count": success_count,
                    "success_rate": percentage(
                        success_count, row["transaction_count"]
                    ),
                }
            )
        return {"grain": "monthly", "series": series, "summary": all_trend["summary"]}

    @translate_service_errors
    def get_growth_overview(self) -> dict[str, Any]:
        """All-time growth overview of the platform.

        Purpose:
            The growth story in one object.

        Business Meaning:
            Where the platform started, where it is now, its best and
            worst growth months, and its average monthly growth.

        Returns:
            Dict with ``first_month`` / ``latest_month`` (period, count,
            amount), ``overall_count_growth_pct``,
            ``overall_amount_growth_pct``,
            ``average_monthly_count_growth_pct``, ``best_growth_month``,
            ``worst_growth_month``.
        """

        series = self.get_portfolio_trend()["series"]
        if not series:
            return {
                "first_month": None,
                "latest_month": None,
                "overall_count_growth_pct": None,
                "overall_amount_growth_pct": None,
                "average_monthly_count_growth_pct": None,
                "best_growth_month": None,
                "worst_growth_month": None,
            }
        first, latest = series[0], series[-1]
        growth_months = [
            row for row in series if row["count_change_pct"] is not None
        ]
        best = max(growth_months, key=lambda r: r["count_change_pct"], default=None)
        worst = min(growth_months, key=lambda r: r["count_change_pct"], default=None)
        average_growth = (
            round(
                sum(r["count_change_pct"] for r in growth_months)
                / len(growth_months),
                2,
            )
            if growth_months
            else None
        )
        return {
            "first_month": _month_point(first),
            "latest_month": _month_point(latest),
            "overall_count_growth_pct": percent_change(
                latest["transaction_count"], first["transaction_count"]
            ),
            "overall_amount_growth_pct": percent_change(
                latest["total_amount"], first["total_amount"]
            ),
            "average_monthly_count_growth_pct": average_growth,
            "best_growth_month": _month_point(best) if best else None,
            "worst_growth_month": _month_point(worst) if worst else None,
        }

    @translate_service_errors
    def get_business_health(self) -> dict[str, Any]:
        """Deterministic business-health indicators with momentum.

        Purpose:
            The health block of executive reporting.

        Business Meaning:
            Current reliability and scale, and whether each is improving
            or deteriorating month over month — reported descriptively,
            without verdicts.

        Returns:
            Dict with ``current`` (all-time KPI bundle) and ``momentum``
            (latest full month vs the month before: counts, volume,
            success-rate point change).
        """

        current = self._kpis.get_transaction_kpis()
        series = self.get_portfolio_trend()["series"]
        momentum: dict[str, Any] = {
            "latest_month": None,
            "previous_month": None,
            "count_change_pct": None,
            "amount_change_pct": None,
            "success_rate_change_points": None,
        }
        if len(series) >= 2:
            latest, previous = series[-1], series[-2]
            momentum = {
                "latest_month": latest["period"],
                "previous_month": previous["period"],
                "count_change_pct": latest["count_change_pct"],
                "amount_change_pct": latest["amount_change_pct"],
                "success_rate_change_points": round(
                    latest["success_rate"] - previous["success_rate"], 2
                ),
            }
        return {"current": current, "momentum": momentum}

    @translate_service_errors
    def compare_periods(
        self,
        current_start: date,
        current_end: date,
        previous_start: date,
        previous_end: date,
    ) -> dict[str, Any]:
        """Compare portfolio KPIs across two periods.

        Purpose:
            The standard "this period vs last period" executive view.

        Business Meaning:
            Side-by-side KPI bundles with the change of every headline
            figure — the raw material of quarter and month reviews.

        Parameters:
            current_start: Current period first day (inclusive).
            current_end: Current period last day (inclusive).
            previous_start: Comparison period first day (inclusive).
            previous_end: Comparison period last day (inclusive).

        Returns:
            Dict with ``current`` and ``previous`` KPI bundles (with the
            period bounds attached) and ``changes``
            (``transaction_count_pct``, ``volume_pct``,
            ``average_amount_pct``, ``success_rate_points``).
        """

        current = self._kpis.get_transaction_kpis(
            start_date=current_start, end_date=current_end
        )
        previous = self._kpis.get_transaction_kpis(
            start_date=previous_start, end_date=previous_end
        )
        return {
            "current": {
                "start_date": current_start,
                "end_date": current_end,
                **current,
            },
            "previous": {
                "start_date": previous_start,
                "end_date": previous_end,
                **previous,
            },
            "changes": {
                "transaction_count_pct": percent_change(
                    current["total_transactions"], previous["total_transactions"]
                ),
                "volume_pct": percent_change(
                    current["total_volume"], previous["total_volume"]
                ),
                "average_amount_pct": percent_change(
                    current["average_transaction_amount"],
                    previous["average_transaction_amount"],
                ),
                "success_rate_points": round(
                    current["success_rate"] - previous["success_rate"], 2
                ),
            },
        }


def _month_point(row: dict[str, Any]) -> dict[str, Any]:
    """Reduce a trend row to its identifying point (pure)."""

    return {
        "period": row["period"],
        "transaction_count": row["transaction_count"],
        "total_amount": row["total_amount"],
    }
