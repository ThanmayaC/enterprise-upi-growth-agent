"""Purpose repository — access to the ``purpose_master`` reference table.

Purpose:
    Lookups over payment purposes. Joins to the fact via ``purposecode``.
"""

from __future__ import annotations

from typing import Sequence

from sqlalchemy import select

from app.models import Purpose
from app.repositories.base_repository import BaseRepository, YES_FLAG


class PurposeRepository(BaseRepository[Purpose]):
    """Read-only repository for the purpose master."""

    model = Purpose

    def find_by_category(self, category: str) -> Sequence[Purpose]:
        """List purposes of one category.

        Purpose:
            Category-level slicing of specialized payment flows.

        Parameters:
            category: Purpose category as stored.

        Returns:
            The matching purposes ordered by code.
        """

        stmt = (
            select(Purpose)
            .where(Purpose.category == category)
            .order_by(Purpose.purpose_code.asc())
        )
        return self._execute_all(stmt)

    def find_recurring(self) -> Sequence[Purpose]:
        """List purposes flagged as recurring.

        Purpose:
            The reference subset relevant to mandate/Autopay queries.

        Returns:
            Recurring purposes ordered by code.
        """

        stmt = (
            select(Purpose)
            .where(Purpose.recurring == YES_FLAG)
            .order_by(Purpose.purpose_code.asc())
        )
        return self._execute_all(stmt)
