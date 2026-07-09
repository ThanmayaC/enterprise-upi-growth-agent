"""Response repository — access to the ``response_master`` reference table.

Purpose:
    Lookups over network response codes. Joins to the fact via
    ``responsecode``; resolves codes to their terminal outcome and owner.
"""

from __future__ import annotations

from typing import Sequence

from sqlalchemy import select

from app.models import Response
from app.repositories.base_repository import BaseRepository, YES_FLAG


class ResponseRepository(BaseRepository[Response]):
    """Read-only repository for the response master."""

    model = Response

    def find_by_result(self, result: str) -> Sequence[Response]:
        """List response codes mapping to one terminal outcome.

        Purpose:
            Resolve which codes constitute an outcome (e.g. all codes that
            mean ``FAILURE``) for failure decomposition queries.

        Parameters:
            result: Terminal outcome value (``responseresult``).

        Returns:
            The matching response records ordered by code.
        """

        stmt = (
            select(Response)
            .where(Response.response_result == result)
            .order_by(Response.response_code.asc())
        )
        return self._execute_all(stmt)

    def find_retryable(self) -> Sequence[Response]:
        """List response codes marked retryable.

        Purpose:
            The reference subset used by retry-behaviour queries.

        Returns:
            Retryable response records ordered by code.
        """

        stmt = (
            select(Response)
            .where(Response.retryable == YES_FLAG)
            .order_by(Response.response_code.asc())
        )
        return self._execute_all(stmt)
