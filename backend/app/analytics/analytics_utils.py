"""Shared, pure analytical computations.

Purpose:
    The deterministic math every analytics domain reuses — growth rates,
    shares, rankings, distribution statistics, and calendar bucketing —
    defined once so no analytical rule is ever duplicated across modules.

Enterprise notes:
    - Every function is a pure function of its inputs: no services, no
      I/O, no randomness — analytics stay deterministic and testable.
    - Monetary shares/changes accept ``Decimal`` and return ``float``
      percentages (2 decimals), matching the service layer's rate
      conventions.
"""

from __future__ import annotations

import statistics
from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Sequence

from app.analytics.analytics_exceptions import InvalidAnalysisRequestError


def percent_change(current: int | Decimal, previous: int | Decimal) -> float | None:
    """Compute period-over-period change as a percentage.

    Purpose:
        One growth-rate convention platform-wide.

    Parameters:
        current: Value of the current period.
        previous: Value of the previous period.

    Returns:
        Change in percent (2 decimals); ``None`` when the previous value
        is zero (growth from nothing is undefined, not infinite).
    """

    if not previous:
        return None
    return round(float((current - previous) * 100 / previous), 2)


def share_percentage(part: int | Decimal, whole: int | Decimal) -> float:
    """Compute a contribution share as a percentage.

    Purpose:
        One contribution convention platform-wide.

    Parameters:
        part: The contributor's value.
        whole: The total it contributes to.

    Returns:
        ``part / whole`` in percent (2 decimals); ``0.0`` for an empty
        total.
    """

    if not whole:
        return 0.0
    return round(float(part * 100 / whole), 2)


def rank_rows(
    rows: Sequence[dict[str, Any]],
    *,
    by: str,
    descending: bool = True,
    top_n: int | None = None,
) -> list[dict[str, Any]]:
    """Rank result rows by a metric and attach a 1-based ``rank`` key.

    Purpose:
        One ranking convention for every leaderboard the platform emits.

    Parameters:
        rows: The rows to rank (not mutated; copies are returned).
        by: Metric key each row must contain.
        descending: ``True`` ranks highest-first.
        top_n: Keep only the first N ranked rows (``None`` = all).

    Returns:
        Ranked row copies, each extended with ``rank``.

    Raises:
        InvalidAnalysisRequestError: For an unknown metric key or a
            non-positive ``top_n``.
    """

    if rows and by not in rows[0]:
        raise InvalidAnalysisRequestError(
            f"unknown ranking metric '{by}'; available: {sorted(rows[0])}"
        )
    if top_n is not None and top_n < 1:
        raise InvalidAnalysisRequestError(f"top_n must be >= 1, got {top_n}")

    ordered = sorted(rows, key=lambda row: row[by], reverse=descending)
    if top_n is not None:
        ordered = ordered[:top_n]
    return [{**row, "rank": position} for position, row in enumerate(ordered, 1)]


def describe_distribution(values: Sequence[int | float | Decimal]) -> dict[str, Any]:
    """Compute descriptive statistics of a value distribution.

    Purpose:
        One distribution summary (spread and central tendency) for every
        "how is X distributed" analysis.

    Parameters:
        values: The observed values (may be empty).

    Returns:
        Dict with ``count``, ``minimum``, ``maximum``, ``mean``,
        ``median``, ``p25``, ``p75`` (statistics are ``None`` when
        empty).
    """

    if not values:
        return {
            "count": 0,
            "minimum": None,
            "maximum": None,
            "mean": None,
            "median": None,
            "p25": None,
            "p75": None,
        }
    floats = sorted(float(v) for v in values)
    quartiles = (
        statistics.quantiles(floats, n=4) if len(floats) > 1 else [floats[0]] * 3
    )
    return {
        "count": len(floats),
        "minimum": floats[0],
        "maximum": floats[-1],
        "mean": round(statistics.fmean(floats), 2),
        "median": round(statistics.median(floats), 2),
        "p25": round(quartiles[0], 2),
        "p75": round(quartiles[2], 2),
    }


def bucket_counts(
    values: Sequence[int], edges: Sequence[int], labels: Sequence[str]
) -> list[dict[str, Any]]:
    """Count values into labelled half-open buckets.

    Purpose:
        One histogram convention for frequency/volume distributions.

    Parameters:
        values: The observed integer values.
        edges: Ascending lower bounds; bucket *i* covers
            ``edges[i] <= v < edges[i+1]`` (the last bucket is unbounded).
        labels: One label per bucket (``len(labels) == len(edges)``).

    Returns:
        One dict per bucket: ``bucket``, ``count``, ``share``.
    """

    counts = [0] * len(edges)
    for value in values:
        for i in range(len(edges) - 1, -1, -1):
            if value >= edges[i]:
                counts[i] += 1
                break
    total = len(values)
    return [
        {"bucket": label, "count": count, "share": share_percentage(count, total)}
        for label, count in zip(labels, counts)
    ]


def week_start(day: date) -> date:
    """Return the Monday starting the ISO week containing ``day``."""

    return day - timedelta(days=day.weekday())


def quarter_of(month_start: date) -> str:
    """Return the quarter label (e.g. ``2024-Q2``) for a month."""

    return f"{month_start.year}-Q{(month_start.month - 1) // 3 + 1}"


def year_of(month_start: date) -> int:
    """Return the calendar year for a month."""

    return month_start.year


def month_windows(start_date: date, end_date: date) -> list[tuple[date, date]]:
    """Split an inclusive date range into calendar-month windows.

    Purpose:
        Shared calendar math for month-by-month analyses; window edges
        are clamped to the requested range.

    Parameters:
        start_date: First day of the range (inclusive).
        end_date: Last day of the range (inclusive).

    Returns:
        Ordered ``(window_start, window_end)`` tuples, one per calendar
        month touched by the range.

    Raises:
        InvalidAnalysisRequestError: If the range is inverted.
    """

    if start_date > end_date:
        raise InvalidAnalysisRequestError(
            f"start_date {start_date} is after end_date {end_date}"
        )
    windows: list[tuple[date, date]] = []
    cursor = date(start_date.year, start_date.month, 1)
    while cursor <= end_date:
        next_month = (
            date(cursor.year + 1, 1, 1)
            if cursor.month == 12
            else date(cursor.year, cursor.month + 1, 1)
        )
        windows.append(
            (max(cursor, start_date), min(next_month - timedelta(days=1), end_date))
        )
        cursor = next_month
    return windows
