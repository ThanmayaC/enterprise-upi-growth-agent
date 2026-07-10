"""Search router — unified enterprise search across entities.

Consumes the Merchant, Customer, Bank, and PSP services. Merchant/customer
search uses the services' indexed name search; bank/PSP search filters the
small reference lists in memory (≤30 rows). No repository or SQLAlchemy
import.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends

from app.api.core.dependencies import (
    BankServiceDep,
    CustomerServiceDep,
    MerchantServiceDep,
    PspServiceDep,
)
from app.api.core.responses import ERROR_RESPONSES
from app.api.schemas.bank import BankProfile
from app.api.schemas.common import Page, SearchParams
from app.api.schemas.customer import CustomerProfile
from app.api.schemas.merchant import MerchantProfile
from app.api.schemas.psp import PspProfile

router = APIRouter(prefix="/search", tags=["Search"], responses=ERROR_RESPONSES)


def _paginate(rows: list[Any], params: SearchParams) -> Page:
    """Apply order + offset/limit to a name-ordered result list."""

    if params.order == "desc":
        rows = list(reversed(rows))
    page = rows[params.offset : params.offset + params.limit]
    return Page(items=page, limit=params.limit, offset=params.offset, count=len(page))


def _filter_by_name(rows: list[dict], term: str, *fields: str) -> list[dict]:
    """Case-insensitive substring filter over the given profile fields."""

    needle = term.lower()
    return [
        row for row in rows
        if any(needle in str(row.get(f, "")).lower() for f in fields)
    ]


@router.get("/merchants", response_model=Page[MerchantProfile], summary="Search merchants")
def merchants(
    service: MerchantServiceDep, params: Annotated[SearchParams, Depends()]
) -> Page:
    """Search merchants by name (partial, case-insensitive)."""

    rows = service.search_merchants(params.q, limit=params.offset + params.limit)
    return _paginate(rows, params)


@router.get("/customers", response_model=Page[CustomerProfile], summary="Search customers")
def customers(
    service: CustomerServiceDep, params: Annotated[SearchParams, Depends()]
) -> Page:
    """Search customers by name (partial, case-insensitive)."""

    rows = service.search_customers(params.q, limit=params.offset + params.limit)
    return _paginate(rows, params)


@router.get("/banks", response_model=Page[BankProfile], summary="Search banks")
def banks(
    service: BankServiceDep, params: Annotated[SearchParams, Depends()]
) -> Page:
    """Search banks by name or short name (partial, case-insensitive)."""

    matched = _filter_by_name(
        service.list_banks(), params.q, "bank_name", "short_name"
    )
    return _paginate(matched, params)


@router.get("/psps", response_model=Page[PspProfile], summary="Search PSPs")
def psps(
    service: PspServiceDep, params: Annotated[SearchParams, Depends()]
) -> Page:
    """Search PSPs by name or handle (partial, case-insensitive)."""

    matched = _filter_by_name(service.list_psps(), params.q, "psp_name", "handle")
    return _paginate(matched, params)
