"""Shared schemas: request parameters, pagination, money, and health.

Purpose:
    The reusable building blocks every router composes — validated query
    parameter groups (pagination, date range, sorting, search), a generic
    paginated envelope, the money serializer, and the health/transaction
    DTOs shared across domains.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Any, Generic, TypeVar

from fastapi import Query
from pydantic import BaseModel, ConfigDict, Field, PlainSerializer

from app.services import ValidationError

#: Money is carried internally as exact ``Decimal`` and serialized to a JSON
#: number, so every endpoint (typed or dict-based) emits money identically
#: for the React/ECharts consumer.
Money = Annotated[Decimal, PlainSerializer(lambda v: float(v), return_type=float)]

T = TypeVar("T")


# ---------------------------------------------------------------------------
# Request parameter groups (injected with Depends)
# ---------------------------------------------------------------------------
class PaginationParams:
    """Standard limit/offset pagination, bounded to protect the platform."""

    def __init__(
        self,
        limit: Annotated[int, Query(ge=1, le=500, description="Page size (max 500).")] = 50,
        offset: Annotated[int, Query(ge=0, description="Rows to skip.")] = 0,
    ) -> None:
        self.limit = limit
        self.offset = offset


class DateRangeParams:
    """Optional inclusive ``[start_date, end_date]`` filter, validated."""

    def __init__(
        self,
        start_date: Annotated[
            date | None, Query(description="First day (inclusive).")
        ] = None,
        end_date: Annotated[
            date | None, Query(description="Last day (inclusive).")
        ] = None,
    ) -> None:
        if start_date and end_date and start_date > end_date:
            raise ValidationError(
                f"start_date {start_date} is after end_date {end_date}"
            )
        self.start_date = start_date
        self.end_date = end_date


class SortParams:
    """Generic ordering: a metric key and a direction."""

    def __init__(
        self,
        sort_by: Annotated[
            str | None, Query(description="Metric key to order by.")
        ] = None,
        order: Annotated[
            str, Query(pattern="^(asc|desc)$", description="'asc' or 'desc'.")
        ] = "desc",
    ) -> None:
        self.sort_by = sort_by
        self.order = order

    @property
    def descending(self) -> bool:
        return self.order == "desc"


class SearchParams:
    """A paginated, ordered search query."""

    def __init__(
        self,
        q: Annotated[
            str, Query(min_length=1, max_length=100, description="Search term.")
        ],
        limit: Annotated[int, Query(ge=1, le=200, description="Page size.")] = 25,
        offset: Annotated[int, Query(ge=0, description="Rows to skip.")] = 0,
        order: Annotated[
            str, Query(pattern="^(asc|desc)$", description="Name order.")
        ] = "asc",
    ) -> None:
        self.q = q
        self.limit = limit
        self.offset = offset
        self.order = order


# ---------------------------------------------------------------------------
# Response envelopes
# ---------------------------------------------------------------------------
class Page(BaseModel, Generic[T]):
    """A single page of results with pagination echo.

    ``count`` is the number of items on this page. A total-row count is
    intentionally omitted: it would force an extra full-table aggregate on
    every listing at fact-table scale.
    """

    items: list[T]
    limit: int = Field(description="Requested page size.")
    offset: int = Field(description="Requested offset.")
    count: int = Field(description="Number of items on this page.")


class HealthResponse(BaseModel):
    """Application liveness."""

    status: str = Field(examples=["ok"])
    service: str
    version: str
    timestamp: datetime


class DatabaseHealthResponse(BaseModel):
    """Database readiness."""

    status: str = Field(examples=["ok", "unavailable"])
    healthy: bool
    detail: str
    timestamp: datetime


class TransactionSummary(BaseModel):
    """One transaction as a list-row DTO (never an ORM object)."""

    model_config = ConfigDict(extra="allow")

    transaction_id: str
    timestamp: datetime
    date: date
    type: str
    category: str
    amount: Money | None = None
    status: str
    payer_vpa: str
    payer_bank: str
    payer_psp: str
    payee_vpa: str
    payee_name: str
    payee_bank: str
    mcc_code: str | None = None
    error_code: str | None = None


class MessageResponse(BaseModel):
    """A simple informational message."""

    message: str


#: Analytical results (trends, contributions, distributions, growth,
#: executive composites) carry deterministic but shape-rich payloads,
#: including some domain-specific keys. They are exposed as open JSON
#: objects so no analytical field is ever silently dropped by response
#: filtering. Stable resources (profiles, cards, KPIs, rankings) use precise
#: models instead.
AnalyticsResult = dict[str, Any]
