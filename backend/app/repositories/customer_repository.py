"""Customer repository — access to the ``customer_master`` reference table.

Purpose:
    Lookups over the 150,000-row customer master. A customer joins to the
    transaction fact through their UPI address (``payeraddress``).
"""

from __future__ import annotations

from typing import Sequence

from sqlalchemy import select

from app.models import Customer
from app.repositories.base_repository import BaseRepository


class CustomerRepository(BaseRepository[Customer]):
    """Read-only repository for the customer master."""

    model = Customer

    def find_by_vpa(self, vpa: str) -> Customer | None:
        """Look up one customer by UPI address.

        Purpose:
            The join key between customers and the transaction fact.

        Parameters:
            vpa: Customer UPI address (``payeraddress``).

        Returns:
            The customer, or ``None`` if unknown.
        """

        stmt = select(Customer).where(Customer.payer_vpa == vpa)
        return self._execute_one_or_none(stmt)

    def find_by_mobile(self, mobile: str) -> Customer | None:
        """Look up one customer by registered mobile number.

        Purpose:
            Support/dispute flows identify customers by mobile.

        Parameters:
            mobile: Ten-digit registered mobile number.

        Returns:
            The customer, or ``None`` if unknown.
        """

        stmt = select(Customer).where(Customer.mobile == mobile)
        return self._execute_one_or_none(stmt)

    def search_by_name(self, term: str, *, limit: int = 50) -> Sequence[Customer]:
        """Search customers by (partial, case-insensitive) name.

        Purpose:
            Name-based lookup for operational tooling.

        Parameters:
            term: Substring to match within ``customer_name``.
            limit: Maximum matches to return.

        Returns:
            Matching customers ordered by name.
        """

        stmt = (
            select(Customer)
            .where(Customer.customer_name.ilike(f"%{term}%"))
            .order_by(Customer.customer_name.asc())
        )
        return self._execute_all(self._apply_pagination(stmt, limit, 0))

    def find_by_psp(
        self, psp_name: str, *, limit: int | None = None, offset: int = 0
    ) -> Sequence[Customer]:
        """List customers onboarded on one PSP app.

        Purpose:
            PSP-level customer segmentation input.

        Parameters:
            psp_name: PSP display name (``payerpsp``).
            limit: Maximum rows (``None`` = all).
            offset: Rows to skip.

        Returns:
            The PSP's customers ordered by id.
        """

        stmt = (
            select(Customer)
            .where(Customer.payer_psp_name == psp_name)
            .order_by(Customer.customer_id.asc())
        )
        return self._execute_all(self._apply_pagination(stmt, limit, offset))
