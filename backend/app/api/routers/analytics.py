"""Analytics router — time-series analytics and the analytics catalogue.

Exposes the Time Analytics engine (the one analytics family without a
natural domain home) and a catalogue index pointing to the entity-analytics
endpoints, which live on their own domain routers to avoid duplication.
Consumes Time Analytics only; no repository or SQLAlchemy import.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.core.dependencies import TimeAnalyticsDep
from app.api.core.responses import ERROR_RESPONSES
from app.api.schemas.common import AnalyticsResult, DateRangeParams

router = APIRouter(prefix="/analytics", tags=["Analytics"], responses=ERROR_RESPONSES)

_Status = Annotated[
    str | None,
    Query(pattern="^(SUCCESS|FAILURE)$", description="Optional outcome filter."),
]


@router.get("", summary="Analytics catalogue")
def catalogue() -> dict[str, list[str]]:
    """Index of every analytics family and where its endpoints live."""

    return {
        "portfolio": [
            "/portfolio/trends", "/portfolio/growth", "/portfolio/health",
            "/portfolio/compare", "/dashboard/executive",
        ],
        "time": [
            "/analytics/time/daily", "/analytics/time/weekly",
            "/analytics/time/monthly", "/analytics/time/quarterly",
            "/analytics/time/yearly", "/analytics/time/hourly",
            "/analytics/time/summary",
        ],
        "merchant": [
            "/merchants/rankings", "/merchants/contribution",
            "/merchants/distribution", "/merchants/success-rate",
            "/merchants/growth", "/merchants/compare",
        ],
        "customer": [
            "/customers/active", "/customers/activity-distribution",
            "/customers/frequency", "/customers/contribution",
            "/customers/trend", "/customers/compare",
        ],
        "bank": [
            "/banks/rankings", "/banks/contribution",
            "/banks/volume-comparison", "/banks/success-comparison",
            "/banks/{bank_name}/trend",
        ],
        "psp": [
            "/psps/rankings", "/psps/performance", "/psps/contribution",
            "/psps/success-analysis", "/psps/{psp_name}/trend",
        ],
    }


@router.get("/time/daily", response_model=AnalyticsResult, summary="Daily trend")
def daily(
    analytics: TimeAnalyticsDep,
    period: Annotated[DateRangeParams, Depends()],
    status: _Status = None,
) -> AnalyticsResult:
    """Daily activity trend."""

    return analytics.get_daily_trend(
        start_date=period.start_date, end_date=period.end_date, status=status
    )


@router.get("/time/weekly", response_model=AnalyticsResult, summary="Weekly trend")
def weekly(
    analytics: TimeAnalyticsDep,
    period: Annotated[DateRangeParams, Depends()],
    status: _Status = None,
) -> AnalyticsResult:
    """Weekly activity trend (ISO weeks)."""

    return analytics.get_weekly_trend(
        start_date=period.start_date, end_date=period.end_date, status=status
    )


@router.get("/time/monthly", response_model=AnalyticsResult, summary="Monthly trend")
def monthly(
    analytics: TimeAnalyticsDep,
    period: Annotated[DateRangeParams, Depends()],
    status: _Status = None,
) -> AnalyticsResult:
    """Monthly activity trend with month-over-month changes."""

    return analytics.get_monthly_trend(
        start_date=period.start_date, end_date=period.end_date, status=status
    )


@router.get("/time/quarterly", response_model=AnalyticsResult, summary="Quarterly trend")
def quarterly(
    analytics: TimeAnalyticsDep,
    period: Annotated[DateRangeParams, Depends()],
    status: _Status = None,
) -> AnalyticsResult:
    """Quarterly activity trend."""

    return analytics.get_quarterly_trend(
        start_date=period.start_date, end_date=period.end_date, status=status
    )


@router.get("/time/yearly", response_model=AnalyticsResult, summary="Yearly trend")
def yearly(
    analytics: TimeAnalyticsDep,
    period: Annotated[DateRangeParams, Depends()],
    status: _Status = None,
) -> AnalyticsResult:
    """Yearly activity trend."""

    return analytics.get_yearly_trend(
        start_date=period.start_date, end_date=period.end_date, status=status
    )


@router.get("/time/hourly", response_model=AnalyticsResult, summary="Hourly profile")
def hourly(
    analytics: TimeAnalyticsDep,
    start_date: Annotated[date, Query(description="First day (inclusive).")],
    end_date: Annotated[date, Query(description="Last day (inclusive); max 7-day span.")],
) -> AnalyticsResult:
    """Hour-of-day activity profile over a bounded range (max 7 days)."""

    return analytics.get_hourly_profile(start_date, end_date)


@router.get("/time/summary", response_model=AnalyticsResult, summary="Time summary")
def summary(
    analytics: TimeAnalyticsDep, period: Annotated[DateRangeParams, Depends()]
) -> AnalyticsResult:
    """Compact temporal summary: busiest/quietest day and month."""

    return analytics.get_time_summary(
        start_date=period.start_date, end_date=period.end_date
    )
