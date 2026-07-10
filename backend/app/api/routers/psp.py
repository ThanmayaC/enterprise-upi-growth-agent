"""PSP Intelligence router — reference list, statistics, rankings, trends.

Consumes the PSP Service and PSP Analytics. No repository or SQLAlchemy
import.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from app.api.core.dependencies import PspAnalyticsDep, PspServiceDep
from app.api.core.responses import ERROR_RESPONSES
from app.api.schemas.common import AnalyticsResult, DateRangeParams
from app.api.schemas.psp import PspProfile, PspStatistics, PspTrafficRow

router = APIRouter(
    prefix="/psps", tags=["PSP Intelligence"], responses=ERROR_RESPONSES
)

_PspName = Annotated[str, Path(description="PSP display name (e.g. PhonePe).")]


@router.get("", response_model=list[PspProfile], summary="List PSPs")
def list_psps(
    psps: PspServiceDep,
    active_only: Annotated[bool, Query(description="Only active PSPs.")] = False,
) -> list[dict]:
    """The PSP reference list from the master."""

    return psps.list_psps(active_only=active_only)


@router.get("/overview", response_model=list[PspTrafficRow], summary="PSP statistics")
def overview(
    psps: PspServiceDep, period: Annotated[DateRangeParams, Depends()]
) -> list[dict]:
    """Per-PSP traffic statistics, busiest first."""

    return psps.get_psp_overview(
        start_date=period.start_date, end_date=period.end_date
    )


@router.get("/rankings", response_model=list[PspTrafficRow], summary="PSP rankings")
def rankings(
    analytics: PspAnalyticsDep,
    period: Annotated[DateRangeParams, Depends()],
    by: str = "total_transactions",
    descending: bool = True,
    top_n: Annotated[int | None, Query(ge=1, le=50)] = None,
) -> list[dict]:
    """Rank PSPs by a traffic metric."""

    return analytics.get_psp_rankings(
        by=by, descending=descending, top_n=top_n,
        start_date=period.start_date, end_date=period.end_date,
    )


@router.get("/top", response_model=list[PspTrafficRow], summary="Top PSPs")
def top_psps(
    analytics: PspAnalyticsDep,
    period: Annotated[DateRangeParams, Depends()],
    n: Annotated[int, Query(ge=1, le=50)] = 5,
    by: str = "total_transactions",
) -> list[dict]:
    """The N leading PSPs on a metric."""

    return analytics.get_top_psps(
        n=n, by=by, start_date=period.start_date, end_date=period.end_date
    )


@router.get("/performance", response_model=AnalyticsResult, summary="PSP performance")
def performance(
    analytics: PspAnalyticsDep, period: Annotated[DateRangeParams, Depends()]
) -> AnalyticsResult:
    """Performance profile across all PSPs (table plus distribution stats)."""

    return analytics.get_psp_performance(
        start_date=period.start_date, end_date=period.end_date
    )


@router.get("/contribution", response_model=AnalyticsResult, summary="PSP contribution")
def contribution(
    analytics: PspAnalyticsDep,
    period: Annotated[DateRangeParams, Depends()],
    top_n: Annotated[int, Query(ge=1, le=50)] = 5,
) -> AnalyticsResult:
    """PSP contribution and concentration analysis."""

    return analytics.get_psp_contribution(
        top_n=top_n, start_date=period.start_date, end_date=period.end_date
    )


@router.get("/success-analysis", response_model=AnalyticsResult, summary="PSP success")
def success_analysis(
    analytics: PspAnalyticsDep,
    period: Annotated[DateRangeParams, Depends()],
    minimum_transactions: Annotated[int, Query(ge=0)] = 100,
) -> AnalyticsResult:
    """PSP payment-success analysis over qualifying PSPs."""

    return analytics.get_success_analysis(
        minimum_transactions=minimum_transactions,
        start_date=period.start_date, end_date=period.end_date,
    )


@router.get("/{psp_name}/profile", response_model=PspProfile, summary="PSP profile")
def profile(psps: PspServiceDep, psp_name: _PspName) -> dict:
    """One PSP's master profile."""

    return psps.get_psp_profile(psp_name)


@router.get(
    "/{psp_name}/statistics", response_model=PspStatistics, summary="PSP statistics"
)
def statistics(psps: PspServiceDep, psp_name: _PspName) -> dict:
    """One PSP's traffic summary, with its profile."""

    return psps.get_psp_transaction_summary(psp_name)


@router.get("/{psp_name}/trend", response_model=AnalyticsResult, summary="PSP trend")
def trend(
    analytics: PspAnalyticsDep,
    psp_name: _PspName,
    start_date: Annotated[date, Query(description="First day (inclusive).")],
    end_date: Annotated[date, Query(description="Last day (inclusive).")],
) -> AnalyticsResult:
    """Monthly traffic trend for one PSP."""

    return analytics.get_psp_trend(psp_name, start_date, end_date)
