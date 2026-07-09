"""MCC repository — access to the ``mcc_master`` reference table.

Purpose:
    Lookups over merchant category codes, the primary dimension for
    category penetration analytics. Joins to the fact via ``payeemcc``.
"""

from __future__ import annotations

from typing import Sequence

from sqlalchemy import select

from app.models import Mcc
from app.repositories.base_repository import BaseRepository, YES_FLAG


class MccRepository(BaseRepository[Mcc]):
    """Read-only repository for the MCC master."""

    model = Mcc

    def search_by_category(self, term: str, *, limit: int = 50) -> Sequence[Mcc]:
        """Search category codes by (partial, case-insensitive) category name.

        Purpose:
            Human-friendly category lookup (codes are opaque four digits).

        Parameters:
            term: Substring to match within ``category``.
            limit: Maximum matches to return.

        Returns:
            Matching MCC records ordered by category name.
        """

        stmt = (
            select(Mcc)
            .where(Mcc.category.ilike(f"%{term}%"))
            .order_by(Mcc.category.asc())
        )
        return self._execute_all(self._apply_pagination(stmt, limit, 0))

    def find_autopay_possible(self) -> Sequence[Mcc]:
        """List categories where Autopay mandates are possible.

        Purpose:
            The reference subset used by mandate-related queries.

        Returns:
            Autopay-capable MCC records ordered by priority then category.
        """

        stmt = (
            select(Mcc)
            .where(Mcc.autopay_possible == YES_FLAG)
            .order_by(Mcc.autopay_priority.asc(), Mcc.category.asc())
        )
        return self._execute_all(stmt)
