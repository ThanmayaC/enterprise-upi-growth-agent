"""Initiation mode repository — access to ``initiation_mode_master``.

Purpose:
    Lookups over transaction initiation modes (QR, intent, collect, ...).
    Joins to the fact via the two-character ``initiationmode`` code.
"""

from __future__ import annotations

from typing import Sequence

from sqlalchemy import select

from app.models import InitiationMode
from app.repositories.base_repository import BaseRepository, YES_FLAG


class InitiationModeRepository(BaseRepository[InitiationMode]):
    """Read-only repository for the initiation mode master."""

    model = InitiationMode

    def find_by_category(self, category: str) -> Sequence[InitiationMode]:
        """List initiation modes of one category.

        Purpose:
            Category-level slicing of payment-experience queries.

        Parameters:
            category: Mode category as stored.

        Returns:
            The matching modes ordered by code.
        """

        stmt = (
            select(InitiationMode)
            .where(InitiationMode.category == category)
            .order_by(InitiationMode.initiation_mode.asc())
        )
        return self._execute_all(stmt)

    def find_autopay_supported(self) -> Sequence[InitiationMode]:
        """List initiation modes that support Autopay mandates.

        Purpose:
            The reference subset used by mandate-related queries.

        Returns:
            Autopay-capable modes ordered by code.
        """

        stmt = (
            select(InitiationMode)
            .where(InitiationMode.autopay_supported == YES_FLAG)
            .order_by(InitiationMode.initiation_mode.asc())
        )
        return self._execute_all(stmt)
