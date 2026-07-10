"""Enterprise Analytics Engine (Phase 8).

Turns the business Service Layer into analytical insight: portfolio,
merchant, customer, bank, PSP, and time-series analytics. Each module owns
a single business domain and consumes **only** services — never
repositories, SQLAlchemy, or SQL. Outputs are plain DTO-like dicts and
lists (rankings, contributions, distributions, trends, summaries), with no
presentation formatting, so they can be reused unchanged by later phases
(ML, Recommendations, Reports, AI Assistant).

Dependency direction (inward only):
    Repositories ─► Services ─► Analytics ─► (future) API ─► Frontend / AI

Failures surface as :class:`AnalyticsError` (or its subclasses
:class:`DataUnavailableError` / :class:`InvalidAnalysisRequestError`);
service exceptions never leak upward.
"""

from app.analytics.analytics_exceptions import (
    AnalyticsError,
    DataUnavailableError,
    InvalidAnalysisRequestError,
)
from app.analytics.bank_analytics import BankAnalytics
from app.analytics.customer_analytics import CustomerAnalytics
from app.analytics.merchant_analytics import MerchantAnalytics
from app.analytics.portfolio_analytics import PortfolioAnalytics
from app.analytics.psp_analytics import PspAnalytics
from app.analytics.time_analytics import TimeAnalytics

__all__ = [
    "AnalyticsError",
    "DataUnavailableError",
    "InvalidAnalysisRequestError",
    "BankAnalytics",
    "CustomerAnalytics",
    "MerchantAnalytics",
    "PortfolioAnalytics",
    "PspAnalytics",
    "TimeAnalytics",
]
