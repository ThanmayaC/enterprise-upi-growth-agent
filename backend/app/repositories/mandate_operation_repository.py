"""Mandate operation repository — access to ``mandate_operation_master``.

Purpose:
    Lookups over the Autopay mandate lifecycle operations (CREATE,
    EXECUTE, ...). A five-row reference table: the generic base API
    (``find_by_id``, ``find_all``, ``exists``, ``count``, ``filter_by``)
    covers every meaningful operation, so no bespoke queries are added.
"""

from __future__ import annotations

from app.models import MandateOperation
from app.repositories.base_repository import BaseRepository


class MandateOperationRepository(BaseRepository[MandateOperation]):
    """Read-only repository for the mandate operation master."""

    model = MandateOperation
