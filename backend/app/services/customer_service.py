"""Customer Service — business views over customers and their activity.

Purpose:
    Customer profile, activity history, and per-customer summaries,
    combining the customer master with the transaction fact.

Business notes:
    - A customer's transactions are the fact rows where they are the
      payer (their VPA is the join key).
    - A customer's activity is fetched once per call and reused for both
      the history and the summary figures — no duplicate repository calls.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from app.models import Customer, Transaction
from app.repositories import CustomerRepository, TransactionRepository
from app.services.kpi_service import (
    STATUS_SUCCESS,
    money,
    percentage,
)
from app.services.service_exceptions import (
    DataNotFoundError,
    require_non_empty,
    translate_repository_errors,
)
from app.services.transaction_service import transaction_to_summary


def _customer_to_profile(customer: Customer) -> dict[str, Any]:
    """Convert a customer entity to its profile DTO."""

    return {
        "customer_id": customer.customer_id,
        "customer_name": customer.customer_name,
        "vpa": customer.payer_vpa,
        "mobile": customer.mobile,
        "psp": customer.payer_psp_name,
        "bank": customer.payer_bank_name,
        "remitter_bank": customer.remitter_bank_name,
        "account_type": customer.remitter_account_type,
    }


class CustomerService:
    """Business-level customer profiles, activity, and summaries.

    Parameters:
        customer_repository: Customer master access.
        transaction_repository: Fact-table access.
    """

    def __init__(
        self,
        customer_repository: CustomerRepository,
        transaction_repository: TransactionRepository,
    ) -> None:
        self._customers = customer_repository
        self._transactions = transaction_repository

    @translate_repository_errors
    def get_customer_profile(self, customer_id: str) -> dict[str, Any]:
        """Fetch one customer's master profile.

        Purpose:
            The identity card behind customer views.

        Parameters:
            customer_id: Customer master id (e.g. ``CUST0000001``).

        Returns:
            The profile DTO.

        Business:
            Profiles come from the master only — activity is a separate,
            costlier concern (see :meth:`get_customer_summary`).

        Raises:
            DataNotFoundError: If the customer id is unknown.
            ValidationError: If the id is blank.
        """

        customer_id = require_non_empty(customer_id, "customer_id")
        customer = self._customers.find_by_id(customer_id)
        if customer is None:
            raise DataNotFoundError(f"customer '{customer_id}' does not exist")
        return _customer_to_profile(customer)

    @translate_repository_errors
    def find_customer_by_vpa(self, vpa: str) -> dict[str, Any]:
        """Fetch one customer's profile by UPI address.

        Purpose:
            Resolve the fact-table identity back to a master profile.

        Parameters:
            vpa: The customer's UPI address.

        Returns:
            The profile DTO.

        Business:
            The VPA is how customers appear on transactions, so support
            flows usually start here.

        Raises:
            DataNotFoundError: If no customer has this VPA.
            ValidationError: If the VPA is blank.
        """

        vpa = require_non_empty(vpa, "vpa")
        customer = self._customers.find_by_vpa(vpa)
        if customer is None:
            raise DataNotFoundError(f"no customer with VPA '{vpa}'")
        return _customer_to_profile(customer)

    @translate_repository_errors
    def search_customers(self, term: str, *, limit: int = 20) -> list[dict[str, Any]]:
        """Search customers by name.

        Purpose:
            Customer lookup for operational tooling and the API search
            surface — the customer-side counterpart of
            :meth:`MerchantService.search_merchants`.

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
        matches = self._customers.search_by_name(term, limit=limit)
        return [_customer_to_profile(c) for c in matches]

    @translate_repository_errors
    def get_customer_activity(
        self, customer_id: str, *, limit: int = 20
    ) -> list[dict[str, Any]]:
        """List a customer's recent transactions.

        Purpose:
            The transaction history behind customer views.

        Parameters:
            customer_id: Customer master id.
            limit: Maximum transactions to return.

        Returns:
            Summary DTOs, most recent first.

        Business:
            History is payer-side: transactions the customer initiated.

        Raises:
            DataNotFoundError: If the customer id is unknown.
        """

        profile = self.get_customer_profile(customer_id)
        rows = self._transactions.get_transactions_by_customer(
            profile["vpa"], limit=limit
        )
        return [transaction_to_summary(txn) for txn in rows]

    @translate_repository_errors
    def get_customer_summary(self, customer_id: str) -> dict[str, Any]:
        """Compute one customer's profile-plus-activity summary.

        Purpose:
            The complete customer view: identity, lifetime figures, and
            latest activity — from a single fact-table fetch.

        Parameters:
            customer_id: Customer master id.

        Returns:
            Dict with ``profile``, ``total_transactions``,
            ``successful_transactions``, ``success_rate``,
            ``total_spent`` (successful debits), ``first_transaction_date``,
            ``last_transaction_date``, and ``recent_transactions``
            (latest 5 summary DTOs).

        Business:
            An average customer has a handful of transactions, so their
            full history is fetched once and every figure is derived from
            that single result set.

        Raises:
            DataNotFoundError: If the customer id is unknown.
        """

        profile = self.get_customer_profile(customer_id)
        history: list[Transaction] = list(
            self._transactions.get_transactions_by_customer(
                profile["vpa"], limit=None
            )
        )

        successes = [t for t in history if t.status == STATUS_SUCCESS]
        total_spent = money(
            sum(
                (t.transaction_amount for t in successes if t.transaction_amount),
                Decimal("0"),
            )
        )
        dates = [t.transaction_date for t in history]
        return {
            "profile": profile,
            "total_transactions": len(history),
            "successful_transactions": len(successes),
            "success_rate": percentage(len(successes), len(history)),
            "total_spent": total_spent,
            "first_transaction_date": min(dates) if dates else None,
            "last_transaction_date": max(dates) if dates else None,
            "recent_transactions": [
                transaction_to_summary(t) for t in history[:5]
            ],
        }

    # ------------------------------------------------------------------
    # Phase 8 service extension — analytics data provisioning
    # ------------------------------------------------------------------
    @translate_repository_errors
    def count_registered(self) -> int:
        """Count customers registered in the master.

        Purpose:
            The registered-customer denominator for activation analytics.

        Returns:
            The customer master row count.

        Business:
            Registration is master membership; activity is a fact-table
            concern reported separately.
        """

        return self._customers.count()

    @translate_repository_errors
    def get_customer_traffic(
        self, *, start_date: date | None = None, end_date: date | None = None
    ) -> list[dict[str, Any]]:
        """Build the per-customer traffic table for a period.

        Purpose:
            The analytics substrate for transaction-frequency and
            top-customer analysis.

        Parameters:
            start_date: First day (inclusive), or ``None`` for all time.
            end_date: Last day (inclusive), or ``None`` for all time.

        Returns:
            One dict per *active* customer (``customer_vpa``,
            ``transaction_count``, ``total_amount``), most active first.

        Business:
            Only customers with activity in the period appear (an
            all-time call returns ~132k rows — callers should treat this
            as a bulk analytical fetch, not a lookup).
        """

        return [
            {
                "customer_vpa": row.customer_vpa,
                "transaction_count": row.transaction_count,
                "total_amount": row.total_amount,
            }
            for row in self._transactions.group_by_customer(
                start_date=start_date, end_date=end_date
            )
        ]
