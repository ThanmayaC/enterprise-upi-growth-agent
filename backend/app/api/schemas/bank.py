"""Bank schemas — profile, statistics, and traffic response models."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.api.schemas.common import Money


class BankProfile(BaseModel):
    """Bank master profile."""

    model_config = ConfigDict(extra="allow")

    bank_id: str
    bank_name: str
    short_name: str
    bank_type: str
    ifsc_prefix: str
    active: bool


class BankTrafficRow(BaseModel):
    """One bank's traffic row on a given side (issuer/acquirer)."""

    model_config = ConfigDict(extra="allow")

    bank: str
    total_transactions: int
    successful_transactions: int
    success_rate: float
    total_amount: Money
    rank: int | None = None


class BankStatistics(BaseModel):
    """One bank's traffic summary on a side, with its profile."""

    model_config = ConfigDict(extra="allow")

    bank: str
    total_transactions: int
    successful_transactions: int
    success_rate: float
    total_amount: Money
    profile: BankProfile
