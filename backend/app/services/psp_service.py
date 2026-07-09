"""PSP Service — business views over payment service providers.

Purpose:
    PSP profiles and PSP-level transaction statistics, combining the PSP
    master with database-side grouped aggregates of the fact.

Business notes:
    - PSP traffic is payer-side by schema design: the fact carries the
      payer's PSP app by name (``payerpsp``) and the payee PSP only as an
      org id.
    - Per-PSP figures come from grouped aggregates (8 PSPs → tiny result
      sets).
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.models import Psp
from app.repositories import PspRepository, TransactionRepository
from app.services.kpi_service import STATUS_SUCCESS, money, percentage
from app.services.service_exceptions import (
    DataNotFoundError,
    require_non_empty,
    translate_repository_errors,
)


def _psp_to_profile(psp: Psp) -> dict[str, Any]:
    """Convert a PSP entity to its profile DTO."""

    return {
        "psp_id": psp.psp_id,
        "psp_name": psp.psp_name,
        "org_id": psp.org_id,
        "handle": psp.handle,
        "sponsor_bank": psp.sponsor_bank,
        "active": psp.active_flag == "Y",
    }


class PspService:
    """Business-level PSP profiles and transaction statistics.

    Parameters:
        psp_repository: PSP master access.
        transaction_repository: Fact-table access.
    """

    def __init__(
        self,
        psp_repository: PspRepository,
        transaction_repository: TransactionRepository,
    ) -> None:
        self._psps = psp_repository
        self._transactions = transaction_repository

    @translate_repository_errors
    def list_psps(self, *, active_only: bool = False) -> list[dict[str, Any]]:
        """List PSP profiles from the master.

        Purpose:
            The reference list behind PSP pickers and reports.

        Parameters:
            active_only: Restrict to PSPs active on the network.

        Returns:
            Profile DTOs ordered by name.

        Business:
            Inactive PSPs remain for historical joins but are excluded
            from forward-looking views.
        """

        psps = self._psps.find_active() if active_only else self._psps.find_all(
            order_by="psp_name"
        )
        return [_psp_to_profile(p) for p in psps]

    @translate_repository_errors
    def get_psp_profile(self, psp_name: str) -> dict[str, Any]:
        """Fetch one PSP's master profile by display name.

        Purpose:
            The identity card behind PSP views.

        Parameters:
            psp_name: PSP display name (as carried on the fact).

        Returns:
            The profile DTO.

        Business:
            PSPs are keyed by display name because that is how the network
            reports them on transactions.

        Raises:
            DataNotFoundError: If the PSP is unknown.
            ValidationError: If the name is blank.
        """

        psp_name = require_non_empty(psp_name, "psp_name")
        psp = self._psps.find_by_name(psp_name)
        if psp is None:
            raise DataNotFoundError(f"PSP '{psp_name}' does not exist")
        return _psp_to_profile(psp)

    @translate_repository_errors
    def get_psp_overview(self) -> list[dict[str, Any]]:
        """Summarize transaction traffic per PSP.

        Purpose:
            The PSP traffic table behind PSP reporting.

        Returns:
            Dicts (``psp``, ``total_transactions``,
            ``successful_transactions``, ``success_rate``,
            ``total_amount``), busiest PSP first.

        Business:
            Traffic attributes each transaction to the customer-facing
            (payer-side) PSP app that carried it.
        """

        all_rows = self._transactions.group_by_psp()
        success_by_psp = {
            row.psp: row
            for row in self._transactions.group_by_psp(status=STATUS_SUCCESS)
        }
        overview: list[dict[str, Any]] = []
        for row in all_rows:
            succeeded = success_by_psp.get(row.psp)
            success_count = succeeded.transaction_count if succeeded else 0
            overview.append(
                {
                    "psp": row.psp,
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
        return overview

    @translate_repository_errors
    def get_psp_transaction_summary(self, psp_name: str) -> dict[str, Any]:
        """Compute one PSP's traffic summary.

        Purpose:
            The per-PSP scorecard behind PSP detail views.

        Parameters:
            psp_name: PSP display name.

        Returns:
            Dict with ``profile`` plus this PSP's row of
            :meth:`get_psp_overview` (zeros when it carried no traffic).

        Business:
            A PSP absent from the fact is a valid zero-traffic answer as
            long as it exists in the master.

        Raises:
            DataNotFoundError: If the PSP is unknown to the master.
        """

        profile = self.get_psp_profile(psp_name)
        row = next(
            (
                entry
                for entry in self.get_psp_overview()
                if entry["psp"] == profile["psp_name"]
            ),
            None,
        )
        summary = row or {
            "psp": profile["psp_name"],
            "total_transactions": 0,
            "successful_transactions": 0,
            "success_rate": 0.0,
            "total_amount": Decimal("0.00"),
        }
        summary["profile"] = profile
        return summary
