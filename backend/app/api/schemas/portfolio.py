"""Portfolio schemas — executive KPI and composition response models."""

from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.api.schemas.common import Money


class KpiBundle(BaseModel):
    """The canonical period scorecard (KPI Service ``get_transaction_kpis``)."""

    model_config = ConfigDict(extra="allow")

    total_transactions: int
    successful_transactions: int
    failed_transactions: int
    total_volume: Money
    average_transaction_amount: Money
    success_rate: float
    failure_rate: float
    approval_rate: float


class KpiSnapshot(KpiBundle):
    """The full executive scorecard (bundle plus participant KPIs)."""

    unique_customers: int
    unique_merchants: int


class Participants(BaseModel):
    """Registered master-data participant counts."""

    model_config = ConfigDict(extra="allow")

    registered_customers: int
    registered_merchants: int
    member_banks: int
    member_psps: int


class Coverage(BaseModel):
    """Data coverage of the transaction fact."""

    model_config = ConfigDict(extra="allow")

    first_transaction_date: date | None = None
    last_transaction_date: date | None = None
    days_with_activity: int


class PortfolioSummary(BaseModel):
    """All-time portfolio summary."""

    model_config = ConfigDict(extra="allow")

    kpis: KpiSnapshot
    participants: Participants
    coverage: Coverage


class LeaderItem(BaseModel):
    """One leading participant (bank/PSP/merchant) by traffic."""

    model_config = ConfigDict(extra="allow")

    name: str
    transaction_count: int
    total_amount: Money


class Leaders(BaseModel):
    """The leading participants across categories."""

    model_config = ConfigDict(extra="allow")

    top_banks: list[LeaderItem]
    top_psps: list[LeaderItem]
    top_merchants: list[dict[str, Any]] = Field(
        description="Top merchants (name, vpa, transaction_count, total_amount)."
    )


class BusinessOverview(BaseModel):
    """Executive business overview: summary plus leaders."""

    model_config = ConfigDict(extra="allow")

    summary: PortfolioSummary
    leaders: Leaders
