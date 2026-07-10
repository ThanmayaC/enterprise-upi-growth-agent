"""Dashboard router — executive cards, quick stats, and recent activity.

Consumes the Dashboard Service (and Portfolio Analytics for the executive
snapshot). No repository or SQLAlchemy import.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.core.dependencies import DashboardServiceDep, PortfolioAnalyticsDep
from app.api.core.responses import ERROR_RESPONSES
from app.api.schemas.common import AnalyticsResult, DateRangeParams, TransactionSummary
from app.api.schemas.dashboard import Card, QuickStats, SystemOverview

router = APIRouter(prefix="/dashboard", tags=["Dashboard"], responses=ERROR_RESPONSES)


@router.get(
    "/cards/portfolio",
    response_model=list[Card],
    summary="Portfolio KPI cards",
)
def portfolio_cards(dashboard: DashboardServiceDep) -> list[dict]:
    """The headline all-time portfolio KPI cards."""

    return dashboard.get_portfolio_cards()


@router.get(
    "/cards/summary",
    response_model=list[Card],
    summary="Period summary cards",
)
def summary_cards(
    dashboard: DashboardServiceDep,
    period: Annotated[DateRangeParams, Depends()],
) -> list[dict]:
    """Period-scoped summary cards (all-time by default)."""

    return dashboard.get_summary_cards(
        start_date=period.start_date, end_date=period.end_date
    )


@router.get("/quick-stats", response_model=QuickStats, summary="Quick stats")
def quick_stats(dashboard: DashboardServiceDep) -> dict:
    """The compact always-visible statistics strip."""

    return dashboard.get_quick_stats()


@router.get(
    "/recent-activity",
    response_model=list[TransactionSummary],
    summary="Recent activity feed",
)
def recent_activity(
    dashboard: DashboardServiceDep,
    limit: Annotated[int, Query(ge=1, le=100, description="Feed length.")] = 10,
) -> list[dict]:
    """The live transaction ticker, most recent first."""

    return dashboard.get_recent_activity(limit=limit)


@router.get(
    "/system-overview",
    response_model=SystemOverview,
    summary="System / reference overview",
)
def system_overview(dashboard: DashboardServiceDep) -> dict:
    """Registered participant counts and active bank/PSP counts."""

    return dashboard.get_system_overview()


@router.get(
    "/executive",
    response_model=AnalyticsResult,
    summary="Executive snapshot",
)
def executive_snapshot(
    analytics: PortfolioAnalyticsDep,
    top_n: Annotated[int, Query(ge=1, le=50, description="Leaders per category.")] = 5,
) -> AnalyticsResult:
    """The complete executive snapshot: KPIs, participants, coverage, leaders."""

    return analytics.get_executive_snapshot(top_n=top_n)
