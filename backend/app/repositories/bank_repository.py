"""Bank repository — access to the ``bank_master`` reference table.

Purpose:
    Lookups over the UPI member banks. Banks join to the transaction fact
    denormalized, by display name (``payerbank`` / ``payeebank``).
"""

from __future__ import annotations

from typing import Sequence

from sqlalchemy import select

from app.models import Bank
from app.repositories.base_repository import BaseRepository, YES_FLAG


class BankRepository(BaseRepository[Bank]):
    """Read-only repository for the bank master."""

    model = Bank

    def find_by_name(self, bank_name: str) -> Bank | None:
        """Look up one bank by display name.

        Purpose:
            The join key between banks and the transaction fact.

        Parameters:
            bank_name: Full bank display name.

        Returns:
            The bank, or ``None`` if unknown.
        """

        stmt = select(Bank).where(Bank.bank_name == bank_name)
        return self._execute_one_or_none(stmt)

    def find_by_type(self, bank_type: str) -> Sequence[Bank]:
        """List banks of one ownership classification.

        Purpose:
            PUBLIC/PRIVATE segmentation input for bank benchmarking.

        Parameters:
            bank_type: Ownership classification as stored.

        Returns:
            The matching banks ordered by name.
        """

        stmt = (
            select(Bank)
            .where(Bank.bank_type == bank_type)
            .order_by(Bank.bank_name.asc())
        )
        return self._execute_all(stmt)

    def find_active(self) -> Sequence[Bank]:
        """List banks whose membership is currently active.

        Purpose:
            Restrict reference joins to live participants.

        Returns:
            Active banks ordered by name.
        """

        stmt = (
            select(Bank)
            .where(Bank.active_flag == YES_FLAG)
            .order_by(Bank.bank_name.asc())
        )
        return self._execute_all(stmt)
