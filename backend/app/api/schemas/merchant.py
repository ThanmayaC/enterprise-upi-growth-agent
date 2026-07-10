"""Merchant schemas — profile, summary, traffic, and request bodies."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.api.schemas.common import Money


class MerchantProfile(BaseModel):
    """Merchant master profile."""

    model_config = ConfigDict(extra="allow")

    merchant_id: str
    merchant_name: str
    verified_name: str
    vpa: str
    mcc_code: str | None = None
    merchant_type: str | None = None
    merchant_genre: str | None = None
    onboarding_type: str | None = None
    psp: str
    bank: str


class MerchantSummary(BaseModel):
    """Merchant profile plus received-payment figures."""

    model_config = ConfigDict(extra="allow")

    profile: MerchantProfile
    total_transactions: int
    successful_transactions: int
    success_rate: float
    total_received: Money


class MerchantTrafficRow(BaseModel):
    """One merchant's traffic row (ranking/leaderboard element)."""

    model_config = ConfigDict(extra="allow")

    merchant_id: str
    merchant_name: str
    vpa: str
    mcc_code: str | None = None
    total_transactions: int
    successful_transactions: int
    success_rate: float
    total_amount: Money
    rank: int | None = None


class MerchantCompareRequest(BaseModel):
    """Body for comparing merchants side by side."""

    merchant_ids: list[str] = Field(
        min_length=2, description="Two or more merchant master ids."
    )
