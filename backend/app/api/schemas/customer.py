"""Customer schemas — profile, summary, traffic, and request bodies."""

from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.api.schemas.common import Money


class CustomerProfile(BaseModel):
    """Customer master profile."""

    model_config = ConfigDict(extra="allow")

    customer_id: str
    customer_name: str
    vpa: str
    mobile: str
    psp: str
    bank: str
    remitter_bank: str
    account_type: str


class CustomerSummary(BaseModel):
    """Customer profile plus lifetime activity figures."""

    model_config = ConfigDict(extra="allow")

    profile: CustomerProfile
    total_transactions: int
    successful_transactions: int
    success_rate: float
    total_spent: Money
    first_transaction_date: date | None = None
    last_transaction_date: date | None = None
    recent_transactions: list[dict[str, Any]]


class CustomerTrafficRow(BaseModel):
    """One customer's traffic row (ranking element)."""

    model_config = ConfigDict(extra="allow")

    customer_vpa: str
    transaction_count: int
    total_amount: Money
    rank: int | None = None


class CustomerCompareRequest(BaseModel):
    """Body for comparing customers side by side."""

    customer_vpas: list[str] = Field(
        min_length=2, description="Two or more customer VPAs."
    )
