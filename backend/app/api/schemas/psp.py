"""PSP schemas — profile, statistics, and traffic response models."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.api.schemas.common import Money


class PspProfile(BaseModel):
    """PSP master profile."""

    model_config = ConfigDict(extra="allow")

    psp_id: str
    psp_name: str
    org_id: str
    handle: str
    sponsor_bank: str
    active: bool


class PspTrafficRow(BaseModel):
    """One PSP's traffic row (ranking element)."""

    model_config = ConfigDict(extra="allow")

    psp: str
    total_transactions: int
    successful_transactions: int
    success_rate: float
    total_amount: Money
    rank: int | None = None


class PspStatistics(BaseModel):
    """One PSP's traffic summary, with its profile."""

    model_config = ConfigDict(extra="allow")

    psp: str
    total_transactions: int
    successful_transactions: int
    success_rate: float
    total_amount: Money
    profile: PspProfile
