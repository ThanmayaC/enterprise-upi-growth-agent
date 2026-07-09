"""Merchant Service — business views over merchants and their activity.

Purpose:
    Merchant profile, lookup, activity, and per-merchant summaries,
    combining the merchant master with the transaction fact.

Business notes:
    - A merchant's transactions are the fact rows where they are the
      payee (their VPA is the join key).
    - Per-merchant figures are read from database-side grouped aggregates
      (500 merchants → tiny result sets), never by materializing a
      merchant's full transaction history.
    - No rankings here — leaderboards belong to Phase 8 analytics.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from app.models import Merchant
from app.repositories import MerchantRepository, TransactionRepository
from app.services.kpi_service import STATUS_SUCCESS, money, percentage
from app.services.service_exceptions import (
    DataNotFoundError,
    require_non_empty,
    translate_repository_errors,
)
from app.services.transaction_service import transaction_to_summary


def _merchant_to_profile(merchant: Merchant) -> dict[str, Any]:
    """Convert a merchant entity to its profile DTO."""

    return {
        "merchant_id": merchant.merchant_id,
        "merchant_name": merchant.merchant_name,
        "verified_name": merchant.verified_name,
        "vpa": merchant.payee_vpa,
        "mcc_code": merchant.mcc_code,
        "merchant_type": merchant.merchant_type,
        "merchant_genre": merchant.merchant_genre,
        "onboarding_type": merchant.onboarding_type,
        "psp": merchant.payee_psp_name,
        "bank": merchant.payee_bank_name,
    }


class MerchantService:
    """Business-level merchant profiles, lookup, activity, and summaries.

    Parameters:
        merchant_repository: Merchant master access.
        transaction_repository: Fact-table access.
    """

    def __init__(
        self,
        merchant_repository: MerchantRepository,
        transaction_repository: TransactionRepository,
    ) -> None:
        self._merchants = merchant_repository
        self._transactions = transaction_repository

    @translate_repository_errors
    def get_merchant_profile(self, merchant_id: str) -> dict[str, Any]:
        """Fetch one merchant's master profile.

        Purpose:
            The identity card behind merchant views.

        Parameters:
            merchant_id: Merchant master id (e.g. ``MER0000001``).

        Returns:
            The profile DTO.

        Business:
            Profiles come from the master only; activity figures are a
            separate concern (see :meth:`get_merchant_summary`).

        Raises:
            DataNotFoundError: If the merchant id is unknown.
            ValidationError: If the id is blank.
        """

        merchant_id = require_non_empty(merchant_id, "merchant_id")
        merchant = self._merchants.find_by_id(merchant_id)
        if merchant is None:
            raise DataNotFoundError(f"merchant '{merchant_id}' does not exist")
        return _merchant_to_profile(merchant)

    @translate_repository_errors
    def search_merchants(self, term: str, *, limit: int = 20) -> list[dict[str, Any]]:
        """Search merchants by name.

        Purpose:
            Merchant lookup for operational tooling.

        Parameters:
            term: Substring matched case-insensitively against names.
            limit: Maximum matches.

        Returns:
            Profile DTOs ordered by name.

        Business:
            Name search is the human entry point; exact identity flows use
            ids or VPAs.

        Raises:
            ValidationError: If the term is blank.
        """

        term = require_non_empty(term, "term")
        matches = self._merchants.search_by_name(term, limit=limit)
        return [_merchant_to_profile(m) for m in matches]

    @translate_repository_errors
    def get_merchant_activity(
        self, merchant_id: str, *, limit: int = 20
    ) -> list[dict[str, Any]]:
        """List a merchant's recent transactions.

        Purpose:
            The transaction feed behind merchant views.

        Parameters:
            merchant_id: Merchant master id.
            limit: Maximum transactions to return.

        Returns:
            Summary DTOs, most recent first.

        Business:
            Activity is payee-side: payments the merchant received.

        Raises:
            DataNotFoundError: If the merchant id is unknown.
        """

        profile = self.get_merchant_profile(merchant_id)
        rows = self._transactions.get_transactions_by_merchant(
            profile["vpa"], limit=limit
        )
        return [transaction_to_summary(txn) for txn in rows]

    @translate_repository_errors
    def get_merchant_summary(self, merchant_id: str) -> dict[str, Any]:
        """Compute one merchant's profile-plus-activity summary.

        Purpose:
            The complete merchant view: identity plus received-payment
            figures.

        Parameters:
            merchant_id: Merchant master id.

        Returns:
            Dict with ``profile``, ``total_transactions``,
            ``successful_transactions``, ``success_rate``, and
            ``total_received`` (successful credits).

        Business:
            Figures come from two database-side grouped aggregates (all
            outcomes and successes); the merchant's rows are picked from
            those small grouped results, so a high-volume merchant costs
            the same as a quiet one.

        Raises:
            DataNotFoundError: If the merchant id is unknown.
        """

        profile = self.get_merchant_profile(merchant_id)
        vpa = profile["vpa"]

        all_rows = self._transactions.group_by_merchant()
        success_rows = self._transactions.group_by_merchant(status=STATUS_SUCCESS)
        total = next(
            (r for r in all_rows if r.merchant_vpa == vpa), None
        )
        succeeded = next(
            (r for r in success_rows if r.merchant_vpa == vpa), None
        )

        total_count = total.transaction_count if total else 0
        success_count = succeeded.transaction_count if succeeded else 0
        return {
            "profile": profile,
            "total_transactions": total_count,
            "successful_transactions": success_count,
            "success_rate": percentage(success_count, total_count),
            "total_received": (
                money(succeeded.total_amount) if succeeded else Decimal("0.00")
            ),
        }

    # ------------------------------------------------------------------
    # Phase 8 service extension — analytics data provisioning
    # ------------------------------------------------------------------
    @translate_repository_errors
    def count_registered(self) -> int:
        """Count merchants registered in the master.

        Purpose:
            The registered-merchant denominator for activation analytics.

        Returns:
            The merchant master row count.

        Business:
            Registration is master membership; activity is a fact-table
            concern reported separately.
        """

        return self._merchants.count()

    @translate_repository_errors
    def get_merchant_traffic(
        self, *, start_date: date | None = None, end_date: date | None = None
    ) -> list[dict[str, Any]]:
        """Build the complete per-merchant traffic table for a period.

        Purpose:
            The analytics substrate for merchant rankings, contribution,
            distribution, growth, and comparisons — one authoritative
            per-merchant table instead of many bespoke queries.

        Parameters:
            start_date: First day (inclusive), or ``None`` for all time.
            end_date: Last day (inclusive), or ``None`` for all time.

        Returns:
            One dict per registered merchant (``merchant_id``,
            ``merchant_name``, ``vpa``, ``mcc_code``,
            ``total_transactions``, ``successful_transactions``,
            ``success_rate``, ``total_amount``), including zero rows for
            merchants without traffic, ordered by merchant id.

        Business:
            Person payees are excluded by construction: only master
            merchants appear. Figures come from two database-side grouped
            aggregates, so cost is independent of merchant size.
        """

        all_rows = {
            row.merchant_vpa: row
            for row in self._transactions.group_by_merchant(
                start_date=start_date, end_date=end_date
            )
        }
        success_rows = {
            row.merchant_vpa: row
            for row in self._transactions.group_by_merchant(
                start_date=start_date, end_date=end_date, status=STATUS_SUCCESS
            )
        }
        traffic: list[dict[str, Any]] = []
        for merchant in self._merchants.find_all(order_by="merchant_id"):
            total = all_rows.get(merchant.payee_vpa)
            succeeded = success_rows.get(merchant.payee_vpa)
            total_count = total.transaction_count if total else 0
            success_count = succeeded.transaction_count if succeeded else 0
            traffic.append(
                {
                    "merchant_id": merchant.merchant_id,
                    "merchant_name": merchant.merchant_name,
                    "vpa": merchant.payee_vpa,
                    "mcc_code": merchant.mcc_code,
                    "total_transactions": total_count,
                    "successful_transactions": success_count,
                    "success_rate": percentage(success_count, total_count),
                    "total_amount": (
                        money(succeeded.total_amount)
                        if succeeded
                        else Decimal("0.00")
                    ),
                }
            )
        return traffic
