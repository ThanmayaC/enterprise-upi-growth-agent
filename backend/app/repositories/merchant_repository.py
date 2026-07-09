"""Merchant repository — access to the ``merchant_master`` reference table.

Purpose:
    Lookups over the 500-row merchant master. A merchant joins to the
    transaction fact through their UPI address (``payeeaddress``).
"""

from __future__ import annotations

from typing import Sequence

from sqlalchemy import select

from app.models import Merchant
from app.repositories.base_repository import BaseRepository


class MerchantRepository(BaseRepository[Merchant]):
    """Read-only repository for the merchant master."""

    model = Merchant

    def find_by_vpa(self, vpa: str) -> Merchant | None:
        """Look up one merchant by UPI address.

        Purpose:
            The join key between merchants and the transaction fact.

        Parameters:
            vpa: Merchant UPI address (``payeeaddress``).

        Returns:
            The merchant, or ``None`` if unknown.
        """

        stmt = select(Merchant).where(Merchant.payee_vpa == vpa)
        return self._execute_one_or_none(stmt)

    def search_by_name(self, term: str, *, limit: int = 50) -> Sequence[Merchant]:
        """Search merchants by (partial, case-insensitive) name.

        Purpose:
            Name-based lookup for operational tooling.

        Parameters:
            term: Substring to match within ``merchant_name``.
            limit: Maximum matches to return.

        Returns:
            Matching merchants ordered by name.
        """

        stmt = (
            select(Merchant)
            .where(Merchant.merchant_name.ilike(f"%{term}%"))
            .order_by(Merchant.merchant_name.asc())
        )
        return self._execute_all(self._apply_pagination(stmt, limit, 0))

    def find_by_mcc(
        self, mcc_code: str, *, limit: int | None = None, offset: int = 0
    ) -> Sequence[Merchant]:
        """List merchants of one category code.

        Purpose:
            Category-level merchant segmentation input.

        Parameters:
            mcc_code: Four-digit merchant category code.
            limit: Maximum rows (``None`` = all).
            offset: Rows to skip.

        Returns:
            The category's merchants ordered by id.
        """

        stmt = (
            select(Merchant)
            .where(Merchant.mcc_code == mcc_code)
            .order_by(Merchant.merchant_id.asc())
        )
        return self._execute_all(self._apply_pagination(stmt, limit, offset))
