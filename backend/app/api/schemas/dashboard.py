"""Dashboard schemas — card and quick-stat response models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

from app.api.schemas.common import Money


class Card(BaseModel):
    """One dashboard card DTO (uniform schema for every card)."""

    model_config = ConfigDict(extra="allow")

    key: str
    title: str
    value: Any
    unit: str


class QuickStats(BaseModel):
    """The compact always-visible statistics strip."""

    model_config = ConfigDict(extra="allow")

    total_transactions: int
    total_volume: Money
    success_rate: float
    approval_rate: float


class SystemOverview(BaseModel):
    """Reference-data overview: what the platform contains."""

    model_config = ConfigDict(extra="allow")

    customers: int
    merchants: int
    banks: int
    psps: int
    active_banks: int
    active_psps: int
