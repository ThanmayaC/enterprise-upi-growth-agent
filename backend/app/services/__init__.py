"""Enterprise Business Service Layer (Phase 7).

Business logic over the repository layer: KPI math (centralized in
:class:`KpiService`), entity-level business views (transactions,
customers, merchants, banks, PSPs), executive portfolio composition, and
DTO-ready dashboard data. Services receive repositories (and, for
composition, other services) by constructor injection and never touch
SQLAlchemy or SQL.

Dependency direction (inward only):
    DashboardService ─► KpiService / TransactionService ─► repositories
    PortfolioService ─► KpiService ────────────────────► repositories
    entity services ───────────────────────────────────► repositories

Failures surface as :class:`ServiceError` (or its subclasses
:class:`DataNotFoundError` / :class:`ValidationError` /
:class:`BusinessRuleError`); repository exceptions never leak upward.
"""

from app.services.bank_service import BankService
from app.services.customer_service import CustomerService
from app.services.dashboard_service import DashboardService
from app.services.kpi_service import KpiService
from app.services.merchant_service import MerchantService
from app.services.portfolio_service import PortfolioService
from app.services.psp_service import PspService
from app.services.service_exceptions import (
    BusinessRuleError,
    DataNotFoundError,
    ServiceError,
    ValidationError,
)
from app.services.transaction_service import TransactionService

__all__ = [
    "ServiceError",
    "DataNotFoundError",
    "ValidationError",
    "BusinessRuleError",
    "BankService",
    "CustomerService",
    "DashboardService",
    "KpiService",
    "MerchantService",
    "PortfolioService",
    "PspService",
    "TransactionService",
]
