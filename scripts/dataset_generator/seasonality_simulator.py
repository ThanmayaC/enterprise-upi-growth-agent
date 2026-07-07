"""
seasonality_simulator.py

Provides date/time weighting so the transaction volume and timing does
not look uniformly random. Models salary days, weekends, and a set of
major Indian festival windows as volume multipliers, plus an
hour-of-day shape for intraday distribution.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from random import Random
from typing import List, Optional

# Festival windows are approximate multi-day spans (month, day) -> span length.
# These act as demand spikes (retail, gifting, travel) independent of year.
FESTIVAL_WINDOWS: tuple[tuple[int, int, int], ...] = (
    (1, 14, 2),   # Makar Sankranti / Pongal
    (3, 8, 2),    # Holi window
    (8, 15, 2),   # Independence Day / Rakhi season
    (9, 7, 5),    # Ganesh Chaturthi window
    (10, 12, 6),  # Navratri/Dussehra window
    (11, 1, 6),   # Diwali window
    (12, 24, 3),  # Christmas / New Year
)

HOURLY_WEIGHTS: tuple[float, ...] = (
    0.2, 0.1, 0.1, 0.1, 0.2, 0.5, 1.0, 1.8,
    2.5, 2.8, 2.6, 2.4, 2.6, 2.4, 2.2, 2.3,
    2.5, 2.8, 3.2, 3.0, 2.4, 1.6, 0.8, 0.4,
)

# Category-specific intraday shapes: office-hour payments cluster 9-18,
# evening food delivery peaks 19-22, night OTT/subscription activity
# clusters late evening/midnight.
OFFICE_HOURS_WEIGHTS: tuple[float, ...] = (
    0.1, 0.1, 0.1, 0.1, 0.1, 0.2, 0.5, 1.2,
    2.8, 3.2, 3.0, 2.8, 2.6, 2.8, 2.9, 2.7,
    2.4, 2.0, 1.2, 0.6, 0.3, 0.2, 0.1, 0.1,
)
EVENING_FOOD_WEIGHTS: tuple[float, ...] = (
    0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.2, 0.4,
    0.6, 0.6, 0.8, 1.4, 1.8, 1.2, 0.8, 0.9,
    1.2, 1.8, 2.8, 3.2, 2.8, 1.8, 0.8, 0.3,
)
NIGHT_OTT_WEIGHTS: tuple[float, ...] = (
    1.4, 1.0, 0.4, 0.2, 0.1, 0.1, 0.1, 0.2,
    0.3, 0.3, 0.3, 0.3, 0.4, 0.4, 0.4, 0.5,
    0.6, 0.8, 1.2, 1.8, 2.6, 3.2, 2.8, 2.0,
)
# Bimodal lunch + dinner spikes for food-service/food-delivery merchants
# (Swiggy/Zomato-style) — sharply peaks ~13:00 and ~20:00-21:00, unlike
# the broad, flat office-hours curve those merchants were previously
# (incorrectly) sharing.
LUNCH_DINNER_WEIGHTS: tuple[float, ...] = (
    0.2, 0.1, 0.1, 0.1, 0.1, 0.1, 0.2, 0.4,
    0.6, 0.8, 1.4, 2.2, 3.4, 3.6, 2.0, 1.0,
    0.8, 1.2, 2.4, 3.8, 3.4, 2.0, 0.9, 0.4,
)
# Bimodal morning + evening commute spikes for fuel stations / transit —
# peaks ~08:00 and ~18:00, matching real commute-driven fuel purchases.
COMMUTE_WEIGHTS: tuple[float, ...] = (
    0.2, 0.1, 0.1, 0.1, 0.2, 0.8, 1.8, 3.0,
    3.6, 2.2, 1.2, 0.9, 0.8, 0.8, 0.9, 1.2,
    1.8, 2.8, 3.4, 2.4, 1.2, 0.6, 0.3, 0.2,
)
HOUR_SHAPE_BY_CATEGORY: dict[str, tuple[float, ...]] = {
    "OFFICE": OFFICE_HOURS_WEIGHTS,
    "EVENING_FOOD": EVENING_FOOD_WEIGHTS,
    "NIGHT_OTT": NIGHT_OTT_WEIGHTS,
    "LUNCH_DINNER": LUNCH_DINNER_WEIGHTS,
    "COMMUTE": COMMUTE_WEIGHTS,
    "DEFAULT": HOURLY_WEIGHTS,
}

# Months (1-indexed) with elevated activity for specific bill categories.
SCHOOL_FEE_MONTHS: frozenset[int] = frozenset({4, 6, 12})           # academic-year admission/term windows
INSURANCE_RENEWAL_MONTHS: frozenset[int] = frozenset({3, 4, 9, 10})  # FY-end and mid-year renewal clusters
TAX_SEASON_MONTHS: frozenset[int] = frozenset({1, 2, 3, 7})          # advance tax + filing season
UTILITY_BILL_DUE_DAYS: tuple[int, ...] = (5, 10, 15, 20, 25)         # typical staggered due-date cycles


class SeasonalitySimulator:
    """Computes per-day volume weights and intraday timing samples."""

    def __init__(self, start_date: date, end_date: date, rng: Random) -> None:
        self.start_date = start_date
        self.end_date = end_date
        self.rng = rng
        self._festival_days = self._expand_festival_days()

    def _expand_festival_days(self) -> set[date]:
        days: set[date] = set()
        for year in range(self.start_date.year, self.end_date.year + 1):
            for month, day, span in FESTIVAL_WINDOWS:
                try:
                    base = date(year, month, day)
                except ValueError:
                    continue
                for offset in range(span):
                    d = base + timedelta(days=offset)
                    if self.start_date <= d <= self.end_date:
                        days.add(d)
        return days

    def is_salary_day(self, d: date) -> bool:
        """Salary days cluster around month-start (1st-3rd) and month-end (28th+)."""
        return d.day <= 3 or d.day >= 28

    def is_weekend(self, d: date) -> bool:
        return d.weekday() >= 5  # Saturday=5, Sunday=6

    def is_festival(self, d: date) -> bool:
        return d in self._festival_days

    def day_weight(self, d: date, weekend_boost: float = 1.0, preferred_weekdays: Optional[List[int]] = None) -> float:
        """Return a relative volume multiplier for the given date.

        weekend_boost lets a specific merchant archetype (e.g. e-commerce,
        food delivery, entertainment) amplify the generic weekend lift
        further than an average merchant. preferred_weekdays lets a
        specific customer's personal habit (e.g. "always orders Swiggy on
        Fridays") add its own independent boost on top."""
        weight = 1.0
        if self.is_salary_day(d):
            weight *= 1.6
        if self.is_weekend(d):
            weight *= 1.25 * weekend_boost
        if self.is_festival(d):
            weight *= 2.0
        if preferred_weekdays and d.weekday() in preferred_weekdays:
            weight *= 1.6
        return weight

    def all_days(self) -> List[date]:
        days = []
        d = self.start_date
        while d <= self.end_date:
            days.append(d)
            d += timedelta(days=1)
        return days

    def sample_day(self, weekend_boost: float = 1.0, preferred_weekdays: Optional[List[int]] = None) -> date:
        """Sample one date from the configured range using day weights."""
        days = self.all_days()
        weights = [self.day_weight(d, weekend_boost, preferred_weekdays) for d in days]
        return self.rng.choices(days, weights=weights, k=1)[0]

    def is_peak_hour(self, hour: int) -> bool:
        """Whether the given hour falls in a high-traffic window per the
        generic intraday demand shape. Used for contextual failure-rate
        modeling (peak-hour congestion), not for timestamp sampling."""
        return HOURLY_WEIGHTS[hour] >= 2.4

    def sample_salary_day(self, weekend_boost: float = 1.0, preferred_weekdays: Optional[List[int]] = None) -> date:
        """Sample a date restricted to salary days (month-start/month-end),
        still honoring weekend/festival weighting within that subset.
        Used to cluster specific customers' activity around salary dates
        based on their persona's salary_day_affinity. Falls back to the
        unrestricted sampler if no salary days fall in the configured range."""
        days = [d for d in self.all_days() if self.is_salary_day(d)]
        if not days:
            return self.sample_day(weekend_boost, preferred_weekdays)
        weights = [self.day_weight(d, weekend_boost, preferred_weekdays) for d in days]
        return self.rng.choices(days, weights=weights, k=1)[0]

    def sample_hour(self) -> int:
        """Sample an hour-of-day (0-23) using the intraday demand shape."""
        return self.rng.choices(range(24), weights=HOURLY_WEIGHTS, k=1)[0]

    def sample_hour_for_category(self, category: str) -> int:
        """Sample an hour-of-day using a category-specific intraday shape.

        category should be one of "OFFICE", "EVENING_FOOD", "NIGHT_OTT",
        or "DEFAULT" (falls back to the generic HOURLY_WEIGHTS shape).
        """
        weights = HOUR_SHAPE_BY_CATEGORY.get(category, HOURLY_WEIGHTS)
        return self.rng.choices(range(24), weights=weights, k=1)[0]

    def is_school_fee_month(self, d: date) -> bool:
        return d.month in SCHOOL_FEE_MONTHS

    def is_insurance_renewal_month(self, d: date) -> bool:
        return d.month in INSURANCE_RENEWAL_MONTHS

    def is_tax_season(self, d: date) -> bool:
        return d.month in TAX_SEASON_MONTHS

    def sample_utility_bill_day(self, year: int, month: int) -> date:
        """Sample a realistic utility bill-due date within the given month."""
        day = self.rng.choice(UTILITY_BILL_DUE_DAYS)
        try:
            return date(year, month, day)
        except ValueError:
            return date(year, month, 28)

    def sample_datetime(self) -> datetime:
        """Sample a full datetime honoring day and intraday seasonality."""
        d = self.sample_day()
        hour = self.sample_hour()
        minute = self.rng.randint(0, 59)
        second = self.rng.randint(0, 59)
        return datetime(d.year, d.month, d.day, hour, minute, second)

    def sample_datetime_for_category(self, category: str) -> datetime:
        """Sample a full datetime using a category-specific intraday shape."""
        d = self.sample_day()
        hour = self.sample_hour_for_category(category)
        minute = self.rng.randint(0, 59)
        second = self.rng.randint(0, 59)
        return datetime(d.year, d.month, d.day, hour, minute, second)
