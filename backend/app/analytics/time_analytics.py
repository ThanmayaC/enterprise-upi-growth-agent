"""Time Analytics — trends of platform activity across every time grain.

Purpose:
    Hourly, daily, weekly, monthly, quarterly, and yearly views of
    transaction activity, each returned as a deterministic trend object:
    the series plus its derived summary (peaks, troughs, averages,
    period-over-period changes).

Business notes:
    - Daily and monthly series come from database-side aggregates via the
      Transaction Service; weekly/quarterly/yearly series are calendar
      roll-ups of those, so every grain reconciles by construction.
    - Amount figures follow the platform volume convention: money that
      moved (successful amounts only) when ``status`` is unfiltered
      would mix outcomes, so amounts are reported per the underlying
      series' status filter.
    - The hourly profile materializes individual transactions and is
      therefore bounded to :data:`MAX_HOURLY_PROFILE_DAYS`.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Callable

from app.analytics.analytics_exceptions import (
    InvalidAnalysisRequestError,
    translate_service_errors,
)
from app.analytics.analytics_utils import (
    percent_change,
    quarter_of,
    week_start,
    year_of,
)
from app.services import TransactionService

#: Upper bound (in days) for the transaction-level hourly profile.
MAX_HOURLY_PROFILE_DAYS = 7

#: Practical page bound when materializing a bounded range of DTOs.
_HOURLY_FETCH_LIMIT = 200_000


class TimeAnalytics:
    """Time-series trends over platform activity.

    Parameters:
        transaction_service: Business-level transaction access.
    """

    def __init__(self, transaction_service: TransactionService) -> None:
        self._transactions = transaction_service

    # ------------------------------------------------------------------
    # Core grains (database-side aggregates)
    # ------------------------------------------------------------------
    @translate_service_errors
    def get_daily_trend(
        self,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        status: str | None = None,
    ) -> dict[str, Any]:
        """Daily activity trend.

        Purpose:
            The day-grain series behind trend analysis.

        Business Meaning:
            Day-level movement of activity: where volume peaked, where it
            troughed, and the average day.

        Parameters:
            start_date: First day (inclusive), or ``None``.
            end_date: Last day (inclusive), or ``None``.
            status: Terminal outcome filter, or ``None`` for all.

        Returns:
            Trend object: ``series`` (chronological ``period``/
            ``transaction_count``/``total_amount`` rows) and ``summary``
            (``total_transactions``, ``total_amount``,
            ``average_transactions_per_period``, ``peak_period``,
            ``trough_period``).
        """

        series = [
            {
                "period": row["day"],
                "transaction_count": row["transaction_count"],
                "total_amount": row["total_amount"],
            }
            for row in self._transactions.get_daily_volume(
                start_date=start_date, end_date=end_date, status=status
            )
        ]
        return {"grain": "daily", "series": series, "summary": _summarize(series)}

    @translate_service_errors
    def get_monthly_trend(
        self,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        status: str | None = None,
    ) -> dict[str, Any]:
        """Monthly activity trend with month-over-month changes.

        Purpose:
            The month-grain series behind growth analysis.

        Business Meaning:
            The canonical growth view: each month carries its change
            versus the previous month.

        Parameters:
            start_date: First day (inclusive), or ``None``.
            end_date: Last day (inclusive), or ``None``.
            status: Terminal outcome filter, or ``None`` for all.

        Returns:
            Trend object as in :meth:`get_daily_trend`; each series row
            additionally carries ``count_change_pct`` and
            ``amount_change_pct`` (``None`` for the first month).
        """

        rows = self._transactions.get_monthly_volume(
            start_date=start_date, end_date=end_date, status=status
        )
        series: list[dict[str, Any]] = []
        previous: dict[str, Any] | None = None
        for row in rows:
            entry = {
                "period": row["month"],
                "transaction_count": row["transaction_count"],
                "total_amount": row["total_amount"],
                "count_change_pct": (
                    percent_change(row["transaction_count"], previous["transaction_count"])
                    if previous
                    else None
                ),
                "amount_change_pct": (
                    percent_change(row["total_amount"], previous["total_amount"])
                    if previous
                    else None
                ),
            }
            series.append(entry)
            previous = entry
        return {"grain": "monthly", "series": series, "summary": _summarize(series)}

    # ------------------------------------------------------------------
    # Roll-up grains (calendar aggregation of the core grains)
    # ------------------------------------------------------------------
    @translate_service_errors
    def get_weekly_trend(
        self,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        status: str | None = None,
    ) -> dict[str, Any]:
        """Weekly activity trend (ISO weeks, Monday-start).

        Purpose:
            The week-grain series for operational cadence analysis.

        Business Meaning:
            Weekly rhythm of the business, free of day-of-week noise.

        Parameters:
            start_date: First day (inclusive), or ``None``.
            end_date: Last day (inclusive), or ``None``.
            status: Terminal outcome filter, or ``None`` for all.

        Returns:
            Trend object; each series ``period`` is the week's Monday.
        """

        daily = self._transactions.get_daily_volume(
            start_date=start_date, end_date=end_date, status=status
        )
        series = _roll_up(daily, "day", lambda d: week_start(d))
        return {"grain": "weekly", "series": series, "summary": _summarize(series)}

    @translate_service_errors
    def get_quarterly_trend(
        self,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        status: str | None = None,
    ) -> dict[str, Any]:
        """Quarterly activity trend.

        Purpose:
            The quarter-grain series for executive review cycles.

        Business Meaning:
            Board-cadence movement of activity and volume.

        Parameters:
            start_date: First day (inclusive), or ``None``.
            end_date: Last day (inclusive), or ``None``.
            status: Terminal outcome filter, or ``None`` for all.

        Returns:
            Trend object; each series ``period`` is a quarter label
            (e.g. ``2024-Q2``).
        """

        monthly = self._transactions.get_monthly_volume(
            start_date=start_date, end_date=end_date, status=status
        )
        series = _roll_up(monthly, "month", quarter_of)
        return {"grain": "quarterly", "series": series, "summary": _summarize(series)}

    @translate_service_errors
    def get_yearly_trend(
        self,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        status: str | None = None,
    ) -> dict[str, Any]:
        """Yearly activity trend.

        Purpose:
            The year-grain series for long-horizon review.

        Business Meaning:
            Annual footprint of the platform.

        Parameters:
            start_date: First day (inclusive), or ``None``.
            end_date: Last day (inclusive), or ``None``.
            status: Terminal outcome filter, or ``None`` for all.

        Returns:
            Trend object; each series ``period`` is a calendar year.
        """

        monthly = self._transactions.get_monthly_volume(
            start_date=start_date, end_date=end_date, status=status
        )
        series = _roll_up(monthly, "month", year_of)
        return {"grain": "yearly", "series": series, "summary": _summarize(series)}

    # ------------------------------------------------------------------
    # Hourly profile (transaction-level, bounded)
    # ------------------------------------------------------------------
    @translate_service_errors
    def get_hourly_profile(self, start_date: date, end_date: date) -> dict[str, Any]:
        """Hour-of-day activity profile over a bounded range.

        Purpose:
            The intraday shape of activity (which hours carry the load).

        Business Meaning:
            Capacity and customer-behaviour insight: the platform's busy
            and quiet hours.

        Parameters:
            start_date: First day (inclusive).
            end_date: Last day (inclusive); the range is capped at
                :data:`MAX_HOURLY_PROFILE_DAYS` days because this profile
                is computed from individual transactions.

        Returns:
            Trend object with 24 rows (``period`` = hour 0–23,
            ``transaction_count``, ``total_amount`` — successful amounts
            only, per the volume convention).

        Raises:
            InvalidAnalysisRequestError: For an inverted or over-long
                range.
        """

        if start_date > end_date:
            raise InvalidAnalysisRequestError(
                f"start_date {start_date} is after end_date {end_date}"
            )
        span_days = (end_date - start_date).days + 1
        if span_days > MAX_HOURLY_PROFILE_DAYS:
            raise InvalidAnalysisRequestError(
                f"hourly profile is limited to {MAX_HOURLY_PROFILE_DAYS} days, "
                f"got {span_days}"
            )

        counts = [0] * 24
        amounts = [Decimal("0")] * 24
        for txn in self._transactions.list_transactions(
            start_date=start_date, end_date=end_date, limit=_HOURLY_FETCH_LIMIT
        ):
            hour = txn["timestamp"].hour
            counts[hour] += 1
            if txn["status"] == "SUCCESS" and txn["amount"] is not None:
                amounts[hour] += txn["amount"]

        series = [
            {
                "period": hour,
                "transaction_count": counts[hour],
                "total_amount": amounts[hour],
            }
            for hour in range(24)
        ]
        return {"grain": "hourly", "series": series, "summary": _summarize(series)}

    # ------------------------------------------------------------------
    # Cross-grain summary
    # ------------------------------------------------------------------
    @translate_service_errors
    def get_time_summary(
        self, *, start_date: date | None = None, end_date: date | None = None
    ) -> dict[str, Any]:
        """Compact time-series summary across grains.

        Purpose:
            One call answering "when is this business busy?".

        Business Meaning:
            The headline temporal facts: busiest and quietest day and
            month, and the average day.

        Parameters:
            start_date: First day (inclusive), or ``None``.
            end_date: Last day (inclusive), or ``None``.

        Returns:
            Dict with ``daily`` and ``monthly`` summary blocks (each per
            :meth:`get_daily_trend`'s ``summary``) and
            ``days_with_activity``.
        """

        daily = self.get_daily_trend(start_date=start_date, end_date=end_date)
        monthly = self.get_monthly_trend(start_date=start_date, end_date=end_date)
        return {
            "daily": daily["summary"],
            "monthly": monthly["summary"],
            "days_with_activity": len(daily["series"]),
        }


def _roll_up(
    rows: list[dict[str, Any]],
    period_key: str,
    bucket_of: Callable[[date], Any],
) -> list[dict[str, Any]]:
    """Aggregate a finer-grain series into calendar buckets (pure)."""

    buckets: dict[Any, dict[str, Any]] = {}
    for row in rows:
        bucket = bucket_of(row[period_key])
        entry = buckets.setdefault(
            bucket,
            {"period": bucket, "transaction_count": 0, "total_amount": Decimal("0")},
        )
        entry["transaction_count"] += row["transaction_count"]
        entry["total_amount"] += row["total_amount"]
    return [buckets[key] for key in sorted(buckets)]


def _summarize(series: list[dict[str, Any]]) -> dict[str, Any]:
    """Derive the standard trend summary from a series (pure)."""

    if not series:
        return {
            "total_transactions": 0,
            "total_amount": Decimal("0"),
            "average_transactions_per_period": 0.0,
            "peak_period": None,
            "trough_period": None,
        }
    total_count = sum(row["transaction_count"] for row in series)
    peak = max(series, key=lambda row: row["transaction_count"])
    trough = min(series, key=lambda row: row["transaction_count"])
    return {
        "total_transactions": total_count,
        "total_amount": sum((row["total_amount"] for row in series), Decimal("0")),
        "average_transactions_per_period": round(total_count / len(series), 2),
        "peak_period": {
            "period": peak["period"],
            "transaction_count": peak["transaction_count"],
        },
        "trough_period": {
            "period": trough["period"],
            "transaction_count": trough["transaction_count"],
        },
    }
