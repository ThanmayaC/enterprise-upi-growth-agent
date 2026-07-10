"""Portfolio router — executive summary, KPIs, overview, and trends.

Consumes the Portfolio Service, the KPI Service, and Portfolio Analytics.
No repository or SQLAlchemy import.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.core.dependencies import (
    KpiServiceDep,
    PortfolioAnalyticsDep,
    PortfolioServiceDep,
)
from app.api.core.responses import ERROR_RESPONSES
from app.api.schemas.analytics import PeriodComparisonRequest
from app.api.schemas.common import AnalyticsResult, DateRangeParams
from app.api.schemas.portfolio import (
    BusinessOverview,
    KpiBundle,
    PortfolioSummary,
)

router = APIRouter(prefix="/portfolio", tags=["Portfolio"], responses=ERROR_RESPONSES)


@router.get("/summary", response_model=PortfolioSummary, summary="Portfolio summary")
def portfolio_summary(portfolio: PortfolioServiceDep) -> dict:
    """All-time portfolio summary: KPI snapshot, participants, coverage."""

    return portfolio.get_portfolio_summary()


@router.get("/overview", response_model=BusinessOverview, summary="Business overview")
def business_overview(
    portfolio: PortfolioServiceDep,
    top_n: Annotated[int, Query(ge=1, le=50, description="Leaders per category.")] = 5,
) -> dict:
    """Executive overview: portfolio summary plus the leading participants."""

    return portfolio.get_business_overview(top_n=top_n)


@router.get("/kpis", response_model=KpiBundle, summary="Portfolio KPIs (period)")
def portfolio_kpis(
    portfolio: PortfolioServiceDep,
    period: Annotated[DateRangeParams, Depends()],
) -> dict:
    """The canonical KPI bundle for an optional period (all-time by default)."""

    return portfolio.get_transaction_summary(
        start_date=period.start_date, end_date=period.end_date
    )


@router.get("/kpis/snapshot", summary="Full KPI snapshot (incl. participants)")
def kpi_snapshot(kpi: KpiServiceDep, period: Annotated[DateRangeParams, Depends()]):
    """The full KPI snapshot including unique customers and merchants.

    Heavier than ``/kpis`` (participant KPIs require full-fact grouping);
    use when the participant counts are actually needed.
    """

    return kpi.get_kpi_snapshot(
        start_date=period.start_date, end_date=period.end_date
    )


@router.get("/trends", response_model=AnalyticsResult, summary="Portfolio trend")
def portfolio_trends(
    analytics: PortfolioAnalyticsDep,
    period: Annotated[DateRangeParams, Depends()],
) -> AnalyticsResult:
    """Monthly portfolio performance trend (counts, volume, reliability)."""

    return analytics.get_portfolio_trend(
        start_date=period.start_date, end_date=period.end_date
    )


@router.get("/growth", response_model=AnalyticsResult, summary="Growth overview")
def growth_overview(analytics: PortfolioAnalyticsDep) -> AnalyticsResult:
    """All-time growth story: first/latest month, best/worst, average growth."""

    return analytics.get_growth_overview()


@router.get("/health", response_model=AnalyticsResult, summary="Business health")
def business_health(analytics: PortfolioAnalyticsDep) -> AnalyticsResult:
    """Deterministic business-health indicators with month-over-month momentum."""

    return analytics.get_business_health()


@router.post("/compare", response_model=AnalyticsResult, summary="Compare periods")
def compare_periods(
    analytics: PortfolioAnalyticsDep, body: PeriodComparisonRequest
) -> AnalyticsResult:
    """Compare portfolio KPIs across two periods with per-metric change."""

    return analytics.compare_periods(
        body.current_start, body.current_end,
        body.previous_start, body.previous_end,
    )
