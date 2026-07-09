"""Error repository — access to the ``error_master`` reference table.

Purpose:
    Lookups over failure classifications. Joins to the fact via
    ``errorcode``; the reference behind error Pareto and failure heatmaps.
"""

from __future__ import annotations

from typing import Sequence

from sqlalchemy import select

from app.models import Error
from app.repositories.base_repository import BaseRepository


class ErrorRepository(BaseRepository[Error]):
    """Read-only repository for the error master."""

    model = Error

    def find_by_severity(self, severity: str) -> Sequence[Error]:
        """List error codes of one severity level.

        Purpose:
            Severity-tiered failure analysis input.

        Parameters:
            severity: Severity level as stored.

        Returns:
            The matching error records ordered by code.
        """

        stmt = (
            select(Error)
            .where(Error.severity == severity)
            .order_by(Error.error_code.asc())
        )
        return self._execute_all(stmt)

    def find_by_owner(self, owner: str) -> Sequence[Error]:
        """List error codes attributed to one owning party.

        Purpose:
            Ownership attribution (bank vs PSP vs network failures).

        Parameters:
            owner: Owning party as stored.

        Returns:
            The matching error records ordered by code.
        """

        stmt = (
            select(Error)
            .where(Error.owner == owner)
            .order_by(Error.error_code.asc())
        )
        return self._execute_all(stmt)
