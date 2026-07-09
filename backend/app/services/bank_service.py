"""Bank Service — business views over banks and their transaction traffic.

Purpose:
    Bank profiles and bank-level transaction statistics, combining the
    bank master with database-side grouped aggregates of the fact.

Business notes:
    - *Issuer* view = the debit (payer/remitter) side of transactions;
      *acquirer* view = the credit (payee/beneficiary) side. Both map to
      the fact's denormalized bank-name columns.
    - Per-bank figures come from grouped aggregates (≤30 banks → tiny
      result sets); a bank's full history is never materialized.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from app.models import Bank
from app.repositories import BankRepository, TransactionRepository
from app.services.kpi_service import STATUS_SUCCESS, money, percentage
from app.services.service_exceptions import (
    DataNotFoundError,
    require_non_empty,
    translate_repository_errors,
)

#: Business terminology → fact-table side mapping.
_ISSUER_SIDE = "payer"
_ACQUIRER_SIDE = "payee"


def _bank_to_profile(bank: Bank) -> dict[str, Any]:
    """Convert a bank entity to its profile DTO."""

    return {
        "bank_id": bank.bank_id,
        "bank_name": bank.bank_name,
        "short_name": bank.bank_short_name,
        "bank_type": bank.bank_type,
        "ifsc_prefix": bank.ifsc_prefix,
        "active": bank.active_flag == "Y",
    }


class BankService:
    """Business-level bank profiles and transaction statistics.

    Parameters:
        bank_repository: Bank master access.
        transaction_repository: Fact-table access.
    """

    def __init__(
        self,
        bank_repository: BankRepository,
        transaction_repository: TransactionRepository,
    ) -> None:
        self._banks = bank_repository
        self._transactions = transaction_repository

    @translate_repository_errors
    def list_banks(self, *, active_only: bool = False) -> list[dict[str, Any]]:
        """List bank profiles from the master.

        Purpose:
            The reference list behind bank pickers and reports.

        Parameters:
            active_only: Restrict to banks with active membership.

        Returns:
            Profile DTOs ordered by name.

        Business:
            Inactive members remain in the master for historical joins but
            are excluded from forward-looking views.
        """

        banks = self._banks.find_active() if active_only else self._banks.find_all(
            order_by="bank_name"
        )
        return [_bank_to_profile(b) for b in banks]

    @translate_repository_errors
    def get_bank_profile(self, bank_name: str) -> dict[str, Any]:
        """Fetch one bank's master profile by display name.

        Purpose:
            The identity card behind bank views.

        Parameters:
            bank_name: Full bank display name (as carried on the fact).

        Returns:
            The profile DTO.

        Business:
            Banks are keyed by display name because that is how the
            network reports them on transactions.

        Raises:
            DataNotFoundError: If the bank is unknown.
            ValidationError: If the name is blank.
        """

        bank_name = require_non_empty(bank_name, "bank_name")
        bank = self._banks.find_by_name(bank_name)
        if bank is None:
            raise DataNotFoundError(f"bank '{bank_name}' does not exist")
        return _bank_to_profile(bank)

    @translate_repository_errors
    def get_issuer_summary(
        self, *, start_date: date | None = None, end_date: date | None = None
    ) -> list[dict[str, Any]]:
        """Summarize transaction traffic per issuing (debit-side) bank.

        Purpose:
            The issuer-side traffic table behind bank reporting.

        Parameters:
            start_date: First day (inclusive), or ``None`` for all time.
            end_date: Last day (inclusive), or ``None`` for all time.

        Returns:
            Dicts (``bank``, ``total_transactions``,
            ``successful_transactions``, ``success_rate``,
            ``total_amount``), busiest bank first.

        Business:
            Issuer view attributes each transaction to the customer's
            (payer's) bank — the side that authorizes the debit.
        """

        return self._side_summary(
            _ISSUER_SIDE, start_date=start_date, end_date=end_date
        )

    @translate_repository_errors
    def get_acquirer_summary(
        self, *, start_date: date | None = None, end_date: date | None = None
    ) -> list[dict[str, Any]]:
        """Summarize transaction traffic per acquiring (credit-side) bank.

        Purpose:
            The acquirer-side traffic table behind bank reporting.

        Parameters:
            start_date: First day (inclusive), or ``None`` for all time.
            end_date: Last day (inclusive), or ``None`` for all time.

        Returns:
            Same shape as :meth:`get_issuer_summary`, credit side.

        Business:
            Acquirer view attributes each transaction to the payee's bank
            — the side that receives the credit.
        """

        return self._side_summary(
            _ACQUIRER_SIDE, start_date=start_date, end_date=end_date
        )

    @translate_repository_errors
    def get_bank_transaction_summary(
        self, bank_name: str, *, side: str = _ISSUER_SIDE
    ) -> dict[str, Any]:
        """Compute one bank's traffic summary on one side.

        Purpose:
            The per-bank scorecard behind bank detail views.

        Parameters:
            bank_name: Full bank display name.
            side: ``"payer"`` (issuer view) or ``"payee"`` (acquirer view).

        Returns:
            Dict with ``profile`` plus the summary fields of
            :meth:`get_issuer_summary` for this bank (zeros when the bank
            had no traffic on that side).

        Business:
            A bank absent from the fact is still a valid answer — a
            zero-traffic summary, not an error — as long as it exists in
            the master.

        Raises:
            DataNotFoundError: If the bank is unknown to the master.
        """

        profile = self.get_bank_profile(bank_name)
        row = next(
            (
                entry
                for entry in self._side_summary(side)
                if entry["bank"] == profile["bank_name"]
            ),
            None,
        )
        summary = row or {
            "bank": profile["bank_name"],
            "total_transactions": 0,
            "successful_transactions": 0,
            "success_rate": 0.0,
            "total_amount": Decimal("0.00"),
        }
        summary["profile"] = profile
        return summary

    # ------------------------------------------------------------------
    def _side_summary(
        self,
        side: str,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[dict[str, Any]]:
        """Build the per-bank traffic table for one transaction side."""

        all_rows = self._transactions.group_by_bank(
            side=side, start_date=start_date, end_date=end_date
        )
        success_by_bank = {
            row.bank: row
            for row in self._transactions.group_by_bank(
                side=side,
                start_date=start_date,
                end_date=end_date,
                status=STATUS_SUCCESS,
            )
        }
        summary: list[dict[str, Any]] = []
        for row in all_rows:
            succeeded = success_by_bank.get(row.bank)
            success_count = succeeded.transaction_count if succeeded else 0
            summary.append(
                {
                    "bank": row.bank,
                    "total_transactions": row.transaction_count,
                    "successful_transactions": success_count,
                    "success_rate": percentage(success_count, row.transaction_count),
                    "total_amount": (
                        money(succeeded.total_amount)
                        if succeeded
                        else Decimal("0.00")
                    ),
                }
            )
        return summary
