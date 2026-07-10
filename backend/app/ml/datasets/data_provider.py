"""MLDataProvider — the ML layer's only integration point with the platform.

Purpose:
    Turn Analytics- and Service-layer outputs into tidy pandas frames the
    feature transformers consume. This is the *single* place the ML platform
    reaches into the rest of the backend, and it does so strictly through the
    Analytics and Service layers — never SQL, repositories, or ORM models.

Design:
    - The provider owns a small composition root (repositories → services →
      analytics) built from an injected SQLAlchemy ``Session``. That wiring
      mirrors the API layer's dependency graph exactly; no business logic is
      re-implemented here.
    - Every method returns a ``DataFrame`` with stable, documented columns so
      transformers and trainers never depend on service dict shapes directly.
"""

from __future__ import annotations

from datetime import date

import pandas as pd

from app.analytics import CustomerAnalytics, MerchantAnalytics, TimeAnalytics
from app.repositories import (
    CustomerRepository,
    MerchantRepository,
    TransactionRepository,
)
from app.services import (
    CustomerService,
    KpiService,
    MerchantService,
    TransactionService,
)
from sqlalchemy.orm import Session


class MLDataProvider:
    """Provide feature-ready frames from the Analytics and Service layers.

    Parameters:
        session: An open SQLAlchemy session (owned by the caller).
    """

    def __init__(self, session: Session) -> None:
        # Composition root — Repositories → Services → Analytics.
        txr = TransactionRepository(session)
        mr = MerchantRepository(session)
        cr = CustomerRepository(session)
        kpi = KpiService(txr, mr)
        self._transactions = TransactionService(txr, kpi)
        self._merchant_analytics = MerchantAnalytics(MerchantService(mr, txr))
        self._customer_analytics = CustomerAnalytics(CustomerService(cr, txr))
        self._time_analytics = TimeAnalytics(self._transactions)
        # Frame memo: several trainers request identical windows — each
        # distinct (method, args) frame is fetched once per provider.
        self._cache: dict[tuple, pd.DataFrame] = {}

    def _memo(self, key: tuple, build) -> pd.DataFrame:
        """Return a defensive copy of the cached frame for ``key``."""

        if key not in self._cache:
            self._cache[key] = build()
        return self._cache[key].copy()

    # ------------------------------------------------------------------
    # Merchant frames
    # ------------------------------------------------------------------
    def merchant_traffic(
        self, start: date | None = None, end: date | None = None
    ) -> pd.DataFrame:
        """Per-merchant traffic table for a period (all registered merchants).

        Columns: merchant_id, merchant_name, mcc_code, total_transactions,
        successful_transactions, success_rate, total_amount.
        """

        def build() -> pd.DataFrame:
            rows = self._merchant_analytics.get_merchant_rankings(
                by="total_transactions", top_n=None,
                start_date=start, end_date=end,
            )
            return pd.DataFrame(rows)

        return self._memo(("merchant_traffic", start, end), build)

    def merchant_growth(
        self,
        current: tuple[date, date],
        previous: tuple[date, date],
    ) -> pd.DataFrame:
        """Per-merchant growth between two periods (all merchants).

        Columns: merchant_id, merchant_name, current_transactions,
        previous_transactions, count_change, count_change_pct,
        current_amount, previous_amount, amount_change.
        """

        result = self._merchant_analytics.get_merchant_growth(
            current[0], current[1], previous[0], previous[1], top_n=None
        )
        return pd.DataFrame(result["fastest_growing"])

    # ------------------------------------------------------------------
    # Customer frames
    # ------------------------------------------------------------------
    def customer_traffic(
        self,
        start: date | None = None,
        end: date | None = None,
        limit: int = 40_000,
    ) -> pd.DataFrame:
        """Per-customer traffic table for a period (most active first, capped).

        Columns: customer_vpa, transaction_count, total_amount.
        """

        def build() -> pd.DataFrame:
            rows = self._customer_analytics.get_top_customers(
                n=limit, by="transaction_count", start_date=start, end_date=end
            )
            return pd.DataFrame(rows)

        return self._memo(("customer_traffic", start, end, limit), build)

    # ------------------------------------------------------------------
    # Transaction frames
    # ------------------------------------------------------------------
    def transaction_sample(
        self, start: date, end: date, limit: int = 60_000
    ) -> pd.DataFrame:
        """A bounded sample of transaction summary rows for a period.

        Columns include: type, category, amount, status, payer_bank,
        payer_psp, payee_bank, mcc_code, timestamp.
        """

        def build() -> pd.DataFrame:
            rows = self._transactions.list_transactions(
                start_date=start, end_date=end, limit=limit
            )
            return pd.DataFrame(rows)

        return self._memo(("transaction_sample", start, end, limit), build)

    # ------------------------------------------------------------------
    # Time-series frames
    # ------------------------------------------------------------------
    def daily_series(
        self,
        status: str | None = None,
        start: date | None = None,
        end: date | None = None,
    ) -> pd.DataFrame:
        """Daily activity series. Columns: period, transaction_count, total_amount."""

        trend = self._time_analytics.get_daily_trend(
            start_date=start, end_date=end, status=status
        )
        return pd.DataFrame(trend["series"])

    def monthly_series(
        self,
        status: str | None = None,
        start: date | None = None,
        end: date | None = None,
    ) -> pd.DataFrame:
        """Monthly activity series with month-over-month change columns."""

        trend = self._time_analytics.get_monthly_trend(
            start_date=start, end_date=end, status=status
        )
        return pd.DataFrame(trend["series"])
