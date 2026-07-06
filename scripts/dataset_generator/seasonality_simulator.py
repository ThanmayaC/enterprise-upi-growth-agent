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
from typing import List

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

    def day_weight(self, d: date) -> float:
        """Return a relative volume multiplier for the given date."""
        weight = 1.0
        if self.is_salary_day(d):
            weight *= 1.6
        if self.is_weekend(d):
            weight *= 1.25
        if self.is_festival(d):
            weight *= 2.0
        return weight

    def all_days(self) -> List[date]:
        days = []
        d = self.start_date
        while d <= self.end_date:
            days.append(d)
            d += timedelta(days=1)
        return days

    def sample_day(self) -> date:
        """Sample one date from the configured range using day weights."""
        days = self.all_days()
        weights = [self.day_weight(d) for d in days]
        return self.rng.choices(days, weights=weights, k=1)[0]

    def sample_hour(self) -> int:
        """Sample an hour-of-day (0-23) using the intraday demand shape."""
        return self.rng.choices(range(24), weights=HOURLY_WEIGHTS, k=1)[0]

    def sample_datetime(self) -> datetime:
        """Sample a full datetime honoring day and intraday seasonality."""
        d = self.sample_day()
        hour = self.sample_hour()
        minute = self.rng.randint(0, 59)
        second = self.rng.randint(0, 59)
        return datetime(d.year, d.month, d.day, hour, minute, second)
