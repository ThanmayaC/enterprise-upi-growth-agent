"""Dependency-injection composition root for the API layer.

Purpose:
    Wire Repositories -> Services -> Analytics as FastAPI dependencies and
    expose them to routers as ready-to-use ``Annotated`` types. This is the
    *only* module in ``app.api`` permitted to import repositories: routers
    depend on services and analytics exclusively, never on persistence.

Design:
    - One SQLAlchemy ``Session`` per request. FastAPI caches each dependency
      result within a request, so ``get_db`` runs once and its session is
      shared by every repository — a single unit of work per request, with
      no duplicated construction.
    - The dependency graph mirrors the constructor signatures of the frozen
      Service and Analytics layers exactly; nothing is re-implemented here.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.analytics import (
    BankAnalytics,
    CustomerAnalytics,
    MerchantAnalytics,
    PortfolioAnalytics,
    PspAnalytics,
    TimeAnalytics,
)
from app.db.database import get_db
from app.repositories import (
    BankRepository,
    CustomerRepository,
    MerchantRepository,
    PspRepository,
    TransactionRepository,
)
from app.services import (
    BankService,
    CustomerService,
    DashboardService,
    KpiService,
    MerchantService,
    PortfolioService,
    PspService,
    TransactionService,
)

DbSession = Annotated[Session, Depends(get_db)]


# ---------------------------------------------------------------------------
# Repository providers (internal — never surfaced to routers)
# ---------------------------------------------------------------------------
def get_transaction_repository(db: DbSession) -> TransactionRepository:
    return TransactionRepository(db)


def get_customer_repository(db: DbSession) -> CustomerRepository:
    return CustomerRepository(db)


def get_merchant_repository(db: DbSession) -> MerchantRepository:
    return MerchantRepository(db)


def get_bank_repository(db: DbSession) -> BankRepository:
    return BankRepository(db)


def get_psp_repository(db: DbSession) -> PspRepository:
    return PspRepository(db)


# ---------------------------------------------------------------------------
# Service providers
# ---------------------------------------------------------------------------
def get_kpi_service(
    txr: Annotated[TransactionRepository, Depends(get_transaction_repository)],
    mr: Annotated[MerchantRepository, Depends(get_merchant_repository)],
) -> KpiService:
    return KpiService(txr, mr)


def get_transaction_service(
    txr: Annotated[TransactionRepository, Depends(get_transaction_repository)],
    kpi: Annotated[KpiService, Depends(get_kpi_service)],
) -> TransactionService:
    return TransactionService(txr, kpi)


def get_customer_service(
    cr: Annotated[CustomerRepository, Depends(get_customer_repository)],
    txr: Annotated[TransactionRepository, Depends(get_transaction_repository)],
) -> CustomerService:
    return CustomerService(cr, txr)


def get_merchant_service(
    mr: Annotated[MerchantRepository, Depends(get_merchant_repository)],
    txr: Annotated[TransactionRepository, Depends(get_transaction_repository)],
) -> MerchantService:
    return MerchantService(mr, txr)


def get_bank_service(
    br: Annotated[BankRepository, Depends(get_bank_repository)],
    txr: Annotated[TransactionRepository, Depends(get_transaction_repository)],
) -> BankService:
    return BankService(br, txr)


def get_psp_service(
    pr: Annotated[PspRepository, Depends(get_psp_repository)],
    txr: Annotated[TransactionRepository, Depends(get_transaction_repository)],
) -> PspService:
    return PspService(pr, txr)


def get_portfolio_service(
    kpi: Annotated[KpiService, Depends(get_kpi_service)],
    txr: Annotated[TransactionRepository, Depends(get_transaction_repository)],
    br: Annotated[BankRepository, Depends(get_bank_repository)],
    pr: Annotated[PspRepository, Depends(get_psp_repository)],
    cr: Annotated[CustomerRepository, Depends(get_customer_repository)],
    mr: Annotated[MerchantRepository, Depends(get_merchant_repository)],
) -> PortfolioService:
    return PortfolioService(kpi, txr, br, pr, cr, mr)


def get_dashboard_service(
    kpi: Annotated[KpiService, Depends(get_kpi_service)],
    tsvc: Annotated[TransactionService, Depends(get_transaction_service)],
    br: Annotated[BankRepository, Depends(get_bank_repository)],
    pr: Annotated[PspRepository, Depends(get_psp_repository)],
    cr: Annotated[CustomerRepository, Depends(get_customer_repository)],
    mr: Annotated[MerchantRepository, Depends(get_merchant_repository)],
) -> DashboardService:
    return DashboardService(kpi, tsvc, br, pr, cr, mr)


# ---------------------------------------------------------------------------
# Analytics providers
# ---------------------------------------------------------------------------
def get_time_analytics(
    tsvc: Annotated[TransactionService, Depends(get_transaction_service)],
) -> TimeAnalytics:
    return TimeAnalytics(tsvc)


def get_portfolio_analytics(
    ps: Annotated[PortfolioService, Depends(get_portfolio_service)],
    kpi: Annotated[KpiService, Depends(get_kpi_service)],
    tan: Annotated[TimeAnalytics, Depends(get_time_analytics)],
) -> PortfolioAnalytics:
    return PortfolioAnalytics(ps, kpi, tan)


def get_merchant_analytics(
    msvc: Annotated[MerchantService, Depends(get_merchant_service)],
) -> MerchantAnalytics:
    return MerchantAnalytics(msvc)


def get_customer_analytics(
    csvc: Annotated[CustomerService, Depends(get_customer_service)],
) -> CustomerAnalytics:
    return CustomerAnalytics(csvc)


def get_bank_analytics(
    bsvc: Annotated[BankService, Depends(get_bank_service)],
) -> BankAnalytics:
    return BankAnalytics(bsvc)


def get_psp_analytics(
    psvc: Annotated[PspService, Depends(get_psp_service)],
) -> PspAnalytics:
    return PspAnalytics(psvc)


# ---------------------------------------------------------------------------
# Router-facing injection types (routers import only these)
# ---------------------------------------------------------------------------
TransactionServiceDep = Annotated[TransactionService, Depends(get_transaction_service)]
CustomerServiceDep = Annotated[CustomerService, Depends(get_customer_service)]
MerchantServiceDep = Annotated[MerchantService, Depends(get_merchant_service)]
BankServiceDep = Annotated[BankService, Depends(get_bank_service)]
PspServiceDep = Annotated[PspService, Depends(get_psp_service)]
KpiServiceDep = Annotated[KpiService, Depends(get_kpi_service)]
PortfolioServiceDep = Annotated[PortfolioService, Depends(get_portfolio_service)]
DashboardServiceDep = Annotated[DashboardService, Depends(get_dashboard_service)]

TimeAnalyticsDep = Annotated[TimeAnalytics, Depends(get_time_analytics)]
PortfolioAnalyticsDep = Annotated[PortfolioAnalytics, Depends(get_portfolio_analytics)]
MerchantAnalyticsDep = Annotated[MerchantAnalytics, Depends(get_merchant_analytics)]
CustomerAnalyticsDep = Annotated[CustomerAnalytics, Depends(get_customer_analytics)]
BankAnalyticsDep = Annotated[BankAnalytics, Depends(get_bank_analytics)]
PspAnalyticsDep = Annotated[PspAnalytics, Depends(get_psp_analytics)]
