"""Merchant Intelligence router — search, profile, statistics, analytics.

Consumes the Merchant Service and Merchant Analytics. No repository or
SQLAlchemy import.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from app.api.core.dependencies import MerchantAnalyticsDep, MerchantServiceDep
from app.api.core.responses import ERROR_RESPONSES
from app.api.schemas.analytics import GrowthRequest
from app.api.schemas.common import (
    AnalyticsResult,
    DateRangeParams,
    Page,
    SearchParams,
    TransactionSummary,
)
from app.api.schemas.merchant import (
    MerchantCompareRequest,
    MerchantProfile,
    MerchantSummary,
    MerchantTrafficRow,
)

router = APIRouter(
    prefix="/merchants", tags=["Merchant Intelligence"], responses=ERROR_RESPONSES
)

_MerchantId = Annotated[str, Path(description="Merchant master id (e.g. MER000001).")]


@router.get("/search", response_model=Page[MerchantProfile], summary="Search merchants")
def search_merchants(
    merchants: MerchantServiceDep, params: Annotated[SearchParams, Depends()]
) -> Page[MerchantProfile]:
    """Search merchants by name (partial, case-insensitive), paginated."""

    rows = merchants.search_merchants(params.q, limit=params.offset + params.limit)
    if params.order == "desc":
        rows = list(reversed(rows))
    page = rows[params.offset : params.offset + params.limit]
    return Page(items=page, limit=params.limit, offset=params.offset, count=len(page))


@router.get("/rankings", response_model=list[MerchantTrafficRow], summary="Rankings")
def rankings(
    analytics: MerchantAnalyticsDep,
    period: Annotated[DateRangeParams, Depends()],
    by: Annotated[str, Query(description="Ranking metric key.")] = "total_transactions",
    descending: Annotated[bool, Query(description="Highest first.")] = True,
    top_n: Annotated[int | None, Query(ge=1, le=500, description="Keep top N.")] = None,
) -> list[dict]:
    """Rank merchants by a traffic metric."""

    return analytics.get_merchant_rankings(
        by=by, descending=descending, top_n=top_n,
        start_date=period.start_date, end_date=period.end_date,
    )


@router.get("/top", response_model=list[MerchantTrafficRow], summary="Top merchants")
def top_merchants(
    analytics: MerchantAnalyticsDep,
    period: Annotated[DateRangeParams, Depends()],
    n: Annotated[int, Query(ge=1, le=200)] = 10,
    by: str = "total_transactions",
) -> list[dict]:
    """The N leading merchants on a metric."""

    return analytics.get_top_merchants(
        n=n, by=by, start_date=period.start_date, end_date=period.end_date
    )


@router.get(
    "/bottom", response_model=list[MerchantTrafficRow], summary="Bottom merchants"
)
def bottom_merchants(
    analytics: MerchantAnalyticsDep,
    period: Annotated[DateRangeParams, Depends()],
    n: Annotated[int, Query(ge=1, le=200)] = 10,
    by: str = "total_transactions",
) -> list[dict]:
    """The N weakest merchants on a metric (zero-traffic merchants included)."""

    return analytics.get_bottom_merchants(
        n=n, by=by, start_date=period.start_date, end_date=period.end_date
    )


@router.get("/contribution", response_model=AnalyticsResult, summary="Contribution")
def contribution(
    analytics: MerchantAnalyticsDep,
    period: Annotated[DateRangeParams, Depends()],
    top_n: Annotated[int, Query(ge=1, le=100)] = 10,
) -> AnalyticsResult:
    """Merchant contribution and concentration (Pareto) analysis."""

    return analytics.get_merchant_contribution(
        top_n=top_n, start_date=period.start_date, end_date=period.end_date
    )


@router.get("/distribution", response_model=AnalyticsResult, summary="Distribution")
def distribution(
    analytics: MerchantAnalyticsDep, period: Annotated[DateRangeParams, Depends()]
) -> AnalyticsResult:
    """Distribution of activity across the merchant base."""

    return analytics.get_merchant_distribution(
        start_date=period.start_date, end_date=period.end_date
    )


@router.get("/success-rate", response_model=AnalyticsResult, summary="Success rates")
def success_rate(
    analytics: MerchantAnalyticsDep,
    period: Annotated[DateRangeParams, Depends()],
    minimum_transactions: Annotated[int, Query(ge=0)] = 100,
) -> AnalyticsResult:
    """Merchant success-rate analysis over qualifying merchants."""

    return analytics.get_success_rate_analysis(
        minimum_transactions=minimum_transactions,
        start_date=period.start_date, end_date=period.end_date,
    )


@router.post("/growth", response_model=AnalyticsResult, summary="Merchant growth")
def growth(analytics: MerchantAnalyticsDep, body: GrowthRequest) -> AnalyticsResult:
    """Per-merchant growth between two periods."""

    return analytics.get_merchant_growth(
        body.current_start, body.current_end,
        body.previous_start, body.previous_end,
        top_n=body.top_n,
    )


@router.post(
    "/compare", response_model=list[MerchantTrafficRow], summary="Compare merchants"
)
def compare(
    analytics: MerchantAnalyticsDep,
    body: MerchantCompareRequest,
    period: Annotated[DateRangeParams, Depends()],
) -> list[dict]:
    """Compare named merchants side by side."""

    return analytics.compare_merchants(
        body.merchant_ids, start_date=period.start_date, end_date=period.end_date
    )


@router.get(
    "/{merchant_id}/profile", response_model=MerchantProfile, summary="Merchant profile"
)
def profile(merchants: MerchantServiceDep, merchant_id: _MerchantId) -> dict:
    """One merchant's master profile."""

    return merchants.get_merchant_profile(merchant_id)


@router.get(
    "/{merchant_id}/summary", response_model=MerchantSummary, summary="Merchant summary"
)
def summary(merchants: MerchantServiceDep, merchant_id: _MerchantId) -> dict:
    """One merchant's profile plus received-payment figures."""

    return merchants.get_merchant_summary(merchant_id)


@router.get(
    "/{merchant_id}/activity",
    response_model=list[TransactionSummary],
    summary="Merchant activity",
)
def activity(
    merchants: MerchantServiceDep,
    merchant_id: _MerchantId,
    limit: Annotated[int, Query(ge=1, le=200)] = 20,
) -> list[dict]:
    """One merchant's recent transactions, most recent first."""

    return merchants.get_merchant_activity(merchant_id, limit=limit)
