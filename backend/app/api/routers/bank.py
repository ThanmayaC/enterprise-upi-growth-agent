"""Bank Intelligence router — reference list, statistics, rankings, trends.

Consumes the Bank Service and Bank Analytics. No repository or SQLAlchemy
import.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from app.api.core.dependencies import BankAnalyticsDep, BankServiceDep
from app.api.core.responses import ERROR_RESPONSES
from app.api.schemas.bank import BankProfile, BankStatistics, BankTrafficRow
from app.api.schemas.common import AnalyticsResult, DateRangeParams

router = APIRouter(
    prefix="/banks", tags=["Bank Intelligence"], responses=ERROR_RESPONSES
)

_Side = Annotated[
    str, Query(pattern="^(issuer|acquirer)$", description="'issuer' or 'acquirer'.")
]
_BankName = Annotated[str, Path(description="Full bank display name.")]


@router.get("", response_model=list[BankProfile], summary="List banks")
def list_banks(
    banks: BankServiceDep,
    active_only: Annotated[bool, Query(description="Only active members.")] = False,
) -> list[dict]:
    """The bank reference list from the master."""

    return banks.list_banks(active_only=active_only)


@router.get("/rankings", response_model=list[BankTrafficRow], summary="Bank rankings")
def rankings(
    analytics: BankAnalyticsDep,
    period: Annotated[DateRangeParams, Depends()],
    side: _Side = "issuer",
    by: str = "total_transactions",
    descending: bool = True,
    top_n: Annotated[int | None, Query(ge=1, le=100)] = None,
) -> list[dict]:
    """Rank banks on one side by a traffic metric."""

    return analytics.get_bank_rankings(
        side=side, by=by, descending=descending, top_n=top_n,
        start_date=period.start_date, end_date=period.end_date,
    )


@router.get("/contribution", response_model=AnalyticsResult, summary="Bank contribution")
def contribution(
    analytics: BankAnalyticsDep,
    period: Annotated[DateRangeParams, Depends()],
    side: _Side = "issuer",
    top_n: Annotated[int, Query(ge=1, le=100)] = 10,
) -> AnalyticsResult:
    """Bank contribution and concentration on one side."""

    return analytics.get_bank_contribution(
        side=side, top_n=top_n,
        start_date=period.start_date, end_date=period.end_date,
    )


@router.get("/volume-comparison", response_model=AnalyticsResult, summary="Volume")
def volume_comparison(
    analytics: BankAnalyticsDep,
    period: Annotated[DateRangeParams, Depends()],
    side: _Side = "issuer",
    top_n: Annotated[int | None, Query(ge=1, le=100)] = None,
) -> AnalyticsResult:
    """Compare banks by transaction volume on one side."""

    return analytics.get_volume_comparison(
        side=side, top_n=top_n,
        start_date=period.start_date, end_date=period.end_date,
    )


@router.get("/success-comparison", response_model=AnalyticsResult, summary="Success")
def success_comparison(
    analytics: BankAnalyticsDep,
    period: Annotated[DateRangeParams, Depends()],
    side: _Side = "issuer",
    minimum_transactions: Annotated[int, Query(ge=0)] = 100,
) -> AnalyticsResult:
    """Compare banks by payment success on one side."""

    return analytics.get_success_comparison(
        side=side, minimum_transactions=minimum_transactions,
        start_date=period.start_date, end_date=period.end_date,
    )


@router.get("/issuers", response_model=list[BankTrafficRow], summary="Issuer statistics")
def issuers(
    banks: BankServiceDep, period: Annotated[DateRangeParams, Depends()]
) -> list[dict]:
    """Per-issuing-bank (debit-side) traffic statistics."""

    return banks.get_issuer_summary(
        start_date=period.start_date, end_date=period.end_date
    )


@router.get(
    "/acquirers", response_model=list[BankTrafficRow], summary="Acquirer statistics"
)
def acquirers(
    banks: BankServiceDep, period: Annotated[DateRangeParams, Depends()]
) -> list[dict]:
    """Per-acquiring-bank (credit-side) traffic statistics."""

    return banks.get_acquirer_summary(
        start_date=period.start_date, end_date=period.end_date
    )


@router.get("/{bank_name}/profile", response_model=BankProfile, summary="Bank profile")
def profile(banks: BankServiceDep, bank_name: _BankName) -> dict:
    """One bank's master profile."""

    return banks.get_bank_profile(bank_name)


#: Public API side names map to the Bank Service's internal fact-side names,
#: so the whole bank surface speaks one vocabulary (issuer/acquirer).
_SIDE_TO_FACT = {"issuer": "payer", "acquirer": "payee"}


@router.get(
    "/{bank_name}/statistics", response_model=BankStatistics, summary="Bank statistics"
)
def statistics(
    banks: BankServiceDep, bank_name: _BankName, side: _Side = "issuer"
) -> dict:
    """One bank's traffic summary on one side, with its profile."""

    return banks.get_bank_transaction_summary(
        bank_name, side=_SIDE_TO_FACT[side]
    )


@router.get("/{bank_name}/trend", response_model=AnalyticsResult, summary="Bank trend")
def trend(
    analytics: BankAnalyticsDep,
    bank_name: _BankName,
    start_date: Annotated[date, Query(description="First day (inclusive).")],
    end_date: Annotated[date, Query(description="Last day (inclusive).")],
    side: _Side = "issuer",
) -> AnalyticsResult:
    """Monthly traffic trend for one bank on one side."""

    return analytics.get_bank_trend(bank_name, start_date, end_date, side=side)
