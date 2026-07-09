"""Recurrence pattern repository — access to ``recurrence_pattern_master``.

Purpose:
    Lookups over mandate recurrence rules (MONTHLY, FORTNIGHTLY, ...). An
    eight-row reference table: the generic base API (``find_by_id``,
    ``find_all``, ``exists``, ``count``, ``filter_by``) covers every
    meaningful operation, so no bespoke queries are added.
"""

from __future__ import annotations

from app.models import RecurrencePattern
from app.repositories.base_repository import BaseRepository


class RecurrencePatternRepository(BaseRepository[RecurrencePattern]):
    """Read-only repository for the recurrence pattern master."""

    model = RecurrencePattern
