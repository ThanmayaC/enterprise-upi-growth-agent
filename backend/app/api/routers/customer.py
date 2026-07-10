"""Customer Intelligence router — search, summary, history, analytics.

Consumes the Customer Service and Customer Analytics. No repository or
SQLAlchemy import.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from app.api.core.dependencies import CustomerAnalyticsDep, CustomerServiceDep
from app.api.core.responses import ERROR_RESPONSES
from app.api.schemas.common import (
    AnalyticsResult,
    DateRangeParams,
    Page,
    SearchParams,
    TransactionSummary,
)
from app.api.schemas.customer import (
    CustomerCompareRequest,
    CustomerProfile,
    CustomerSummary,
    CustomerTrafficRow,
)

router = APIRouter(
    prefix="/customers", tags=["Customer Intelligence"], responses=ERROR_RESPONSES
)

_CustomerId = Annotated[str, Path(description="Customer master id (e.g. CUST0000001).")]


@router.get("/search", response_model=Page[CustomerProfile], summary="Search customers")
def search_customers(
    customers: CustomerServiceDep, params: Annotated[SearchParams, Depends()]
) -> Page[CustomerProfile]:
    """Search customers by name (partial, case-insensitive), paginated."""

    rows = customers.search_customers(params.q, limit=params.offset + params.limit)
    if params.order == "desc":
        rows = list(reversed(rows))
    page = rows[params.offset : params.offset + params.limit]
    return Page(items=page, limit=params.limit, offset=params.offset, count=len(page))


@router.get("/by-vpa", response_model=CustomerProfile, summary="Resolve by VPA")
def by_vpa(
    customers: CustomerServiceDep,
    vpa: Annotated[str, Query(min_length=1, description="Customer UPI address.")],
) -> dict:
    """Resolve a fact-table VPA back to a customer master profile."""

    return customers.find_customer_by_vpa(vpa)


@router.get("/active", response_model=AnalyticsResult, summary="Active customers")
def active_customers(
    analytics: CustomerAnalyticsDep, period: Annotated[DateRangeParams, Depends()]
) -> AnalyticsResult:
    """Active vs registered base and activation rate for a period."""

    return analytics.get_active_customers(
        start_date=period.start_date, end_date=period.end_date
    )


@router.get(
    "/activity-distribution",
    response_model=AnalyticsResult,
    summary="Activity distribution",
)
def activity_distribution(
    analytics: CustomerAnalyticsDep, period: Annotated[DateRangeParams, Depends()]
) -> AnalyticsResult:
    """Distribution of activity across active customers."""

    return analytics.get_activity_distribution(
        start_date=period.start_date, end_date=period.end_date
    )


@router.get("/frequency", response_model=AnalyticsResult, summary="Transaction frequency")
def frequency(
    analytics: CustomerAnalyticsDep, period: Annotated[DateRangeParams, Depends()]
) -> AnalyticsResult:
    """How often active customers transact (single vs repeat)."""

    return analytics.get_transaction_frequency(
        start_date=period.start_date, end_date=period.end_date
    )


@router.get("/top", response_model=list[CustomerTrafficRow], summary="Top customers")
def top_customers(
    analytics: CustomerAnalyticsDep,
    period: Annotated[DateRangeParams, Depends()],
    n: Annotated[int, Query(ge=1, le=200)] = 10,
    by: Annotated[str, Query(description="'transaction_count' or 'total_amount'.")] = "transaction_count",
) -> list[dict]:
    """The N most active customers on a metric."""

    return analytics.get_top_customers(
        n=n, by=by, start_date=period.start_date, end_date=period.end_date
    )


@router.get("/contribution", response_model=AnalyticsResult, summary="Contribution")
def contribution(
    analytics: CustomerAnalyticsDep,
    period: Annotated[DateRangeParams, Depends()],
    top_n: Annotated[int, Query(ge=1, le=100)] = 10,
) -> AnalyticsResult:
    """Customer contribution and concentration analysis."""

    return analytics.get_customer_contribution(
        top_n=top_n, start_date=period.start_date, end_date=period.end_date
    )


@router.get("/trend", response_model=AnalyticsResult, summary="Customer trend")
def trend(
    analytics: CustomerAnalyticsDep,
    start_date: Annotated[date, Query(description="First day (inclusive).")],
    end_date: Annotated[date, Query(description="Last day (inclusive).")],
) -> AnalyticsResult:
    """Monthly trend of the active customer base over a range."""

    return analytics.get_customer_trend(start_date, end_date)


@router.post(
    "/compare", response_model=list[CustomerTrafficRow], summary="Compare customers"
)
def compare(
    analytics: CustomerAnalyticsDep,
    body: CustomerCompareRequest,
    period: Annotated[DateRangeParams, Depends()],
) -> list[dict]:
    """Compare named customers side by side."""

    return analytics.compare_customers(
        body.customer_vpas, start_date=period.start_date, end_date=period.end_date
    )


@router.get(
    "/{customer_id}/profile", response_model=CustomerProfile, summary="Customer profile"
)
def profile(customers: CustomerServiceDep, customer_id: _CustomerId) -> dict:
    """One customer's master profile."""

    return customers.get_customer_profile(customer_id)


@router.get(
    "/{customer_id}/summary", response_model=CustomerSummary, summary="Customer summary"
)
def summary(customers: CustomerServiceDep, customer_id: _CustomerId) -> dict:
    """One customer's lifetime activity summary."""

    return customers.get_customer_summary(customer_id)


@router.get(
    "/{customer_id}/history",
    response_model=list[TransactionSummary],
    summary="Customer history",
)
def history(
    customers: CustomerServiceDep,
    customer_id: _CustomerId,
    limit: Annotated[int, Query(ge=1, le=200)] = 20,
) -> list[dict]:
    """One customer's recent transactions, most recent first."""

    return customers.get_customer_activity(customer_id, limit=limit)
