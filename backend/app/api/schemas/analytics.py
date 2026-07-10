"""Analytics schemas — request bodies and lightly-typed result documents.

Analytics outputs (trends, contributions, distributions, growth, executive
composites) are deterministic but shape-rich and occasionally carry
domain-specific keys. They are exposed through the open ``AnalyticsResult``
JSON-object type (see :mod:`app.api.schemas.common`) so no analytical field
is ever dropped by response filtering, while remaining fully documented in
each endpoint's docstring. This module holds the request bodies and the few
stable typed fragments worth pinning.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field, model_validator


class PeriodComparisonRequest(BaseModel):
    """Two inclusive periods to compare (current vs previous)."""

    current_start: date
    current_end: date
    previous_start: date
    previous_end: date

    @model_validator(mode="after")
    def _validate(self) -> "PeriodComparisonRequest":
        if self.current_start > self.current_end:
            raise ValueError("current_start is after current_end")
        if self.previous_start > self.previous_end:
            raise ValueError("previous_start is after previous_end")
        return self


class GrowthRequest(PeriodComparisonRequest):
    """Period comparison with an optional result cap per direction."""

    top_n: int | None = Field(
        default=10, ge=1, description="Rows per direction (null = all)."
    )


class DistributionStats(BaseModel):
    """Descriptive statistics of a value distribution."""

    count: int
    minimum: float | None = None
    maximum: float | None = None
    mean: float | None = None
    median: float | None = None
    p25: float | None = None
    p75: float | None = None
