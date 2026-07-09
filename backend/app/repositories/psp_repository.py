"""PSP repository — access to the ``psp_master`` reference table.

Purpose:
    Lookups over the payment service providers. PSPs join to the
    transaction fact by display name (``payerpsp``) or org id.
"""

from __future__ import annotations

from typing import Sequence

from sqlalchemy import select

from app.models import Psp
from app.repositories.base_repository import BaseRepository, YES_FLAG


class PspRepository(BaseRepository[Psp]):
    """Read-only repository for the PSP master."""

    model = Psp

    def find_by_name(self, psp_name: str) -> Psp | None:
        """Look up one PSP by display name.

        Purpose:
            The join key between PSPs and the transaction fact.

        Parameters:
            psp_name: PSP display name (e.g. ``PhonePe``).

        Returns:
            The PSP, or ``None`` if unknown.
        """

        stmt = select(Psp).where(Psp.psp_name == psp_name)
        return self._execute_one_or_none(stmt)

    def find_by_org_id(self, org_id: str) -> Psp | None:
        """Look up one PSP by network organization id.

        Purpose:
            Resolves the fact's ``payerpsporgid`` / ``payeepsporgid``
            references (the only payee-side PSP identity carried).

        Parameters:
            org_id: Network organization id (e.g. ``ORG0001``).

        Returns:
            The PSP, or ``None`` if unknown.
        """

        stmt = select(Psp).where(Psp.org_id == org_id)
        return self._execute_one_or_none(stmt)

    def find_active(self) -> Sequence[Psp]:
        """List PSPs currently active on the network.

        Purpose:
            Restrict reference joins to live participants.

        Returns:
            Active PSPs ordered by name.
        """

        stmt = (
            select(Psp)
            .where(Psp.active_flag == YES_FLAG)
            .order_by(Psp.psp_name.asc())
        )
        return self._execute_all(stmt)
