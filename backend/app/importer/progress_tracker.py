"""Progress Tracker — console progress display for long-running imports.

Purpose:
    Render an in-place progress line per dataset::

        ████████████░░░░░░░░  62%  625,000/1,012,591 rows  elapsed 28s  ETA 17s  22,321 rows/s

Enterprise notes:
    - Repaints are throttled (time- and percentage-based) so a million-row
      import spends its cycles on inserts, not on console writes.
    - When stdout is not an interactive terminal (CI, redirected logs) the
      in-place repaints are suppressed and only the final state is written,
      keeping captured logs clean.
    - The bar degrades to ASCII characters automatically when the console
      encoding cannot render block glyphs (legacy Windows code pages).
"""

from __future__ import annotations

import sys
import time

_FULL_BLOCK = "█"   # █
_EMPTY_BLOCK = "░"  # ░


def format_duration(seconds: float) -> str:
    """Format a duration compactly for console output.

    Purpose:
        Shared human-readable rendering of elapsed/ETA values ("45s",
        "8m 12s", "1h 04m") used by the tracker and the final summary.

    Parameters:
        seconds: Duration in seconds (negative values are clamped to zero).

    Returns:
        A compact duration string.
    """

    seconds = max(seconds, 0.0)
    if seconds < 60:
        return f"{seconds:.0f}s"
    minutes, secs = divmod(int(seconds), 60)
    if minutes < 60:
        return f"{minutes}m {secs:02d}s"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes:02d}m"


class ProgressTracker:
    """In-place console progress bar with rows, elapsed time, and ETA.

    Purpose:
        Give operators live feedback (percentage, throughput, ETA) during
        each dataset import without flooding the console.

    Parameters:
        label: Dataset label shown above the bar (e.g. ``"Customers"``).
        total: Expected number of rows (used for percentage and ETA; the
            tracker clamps to at least 1 to stay division-safe).
        width: Bar width in characters.
        min_interval: Minimum seconds between repaints at the same
            percentage point.
    """

    def __init__(
        self,
        label: str,
        total: int,
        width: int = 20,
        min_interval: float = 0.5,
    ) -> None:
        self._label = label
        self._total = max(total, 1)
        self._width = width
        self._min_interval = min_interval
        self._started = time.monotonic()
        self._last_paint = 0.0
        self._last_percent = -1
        self._interactive = sys.stdout.isatty()
        self._full, self._empty = self._pick_glyphs()
        if self._interactive:
            sys.stdout.write(f"Importing {label}...\n")
            sys.stdout.flush()

    @staticmethod
    def _pick_glyphs() -> tuple[str, str]:
        """Fall back to ASCII when the console cannot encode block glyphs."""

        encoding = sys.stdout.encoding or "utf-8"
        try:
            (_FULL_BLOCK + _EMPTY_BLOCK).encode(encoding)
        except (UnicodeEncodeError, LookupError):
            return "#", "-"
        return _FULL_BLOCK, _EMPTY_BLOCK

    def update(self, done: int) -> None:
        """Repaint the progress line if enough progress or time has passed.

        Purpose:
            Called by the orchestrator after every batch; throttling keeps
            the cost negligible regardless of call frequency.

        Parameters:
            done: Cumulative number of rows processed so far.

        Returns:
            None.
        """

        if not self._interactive:
            return
        percent = min(int(done * 100 / self._total), 100)
        now = time.monotonic()
        if percent == self._last_percent and (now - self._last_paint) < self._min_interval:
            return
        self._last_percent = percent
        self._last_paint = now
        sys.stdout.write("\r" + self._render(done, percent))
        sys.stdout.flush()

    def finish(self, done: int) -> None:
        """Paint the final state and terminate the progress line.

        Purpose:
            Guarantee a complete, newline-terminated record of the dataset's
            progress in both interactive and non-interactive consoles.

        Parameters:
            done: Final number of rows processed.

        Returns:
            None.
        """

        percent = min(int(done * 100 / self._total), 100)
        prefix = "\r" if self._interactive else f"Importing {self._label}... "
        sys.stdout.write(prefix + self._render(done, percent) + "\n")
        sys.stdout.flush()

    def _render(self, done: int, percent: int) -> str:
        """Compose the progress line: bar, %, rows, elapsed, ETA, rate."""

        filled = min(int(self._width * done / self._total), self._width)
        bar = self._full * filled + self._empty * (self._width - filled)
        elapsed = time.monotonic() - self._started
        rate = done / elapsed if elapsed > 0 else 0.0
        remaining = (self._total - done) / rate if rate > 0 else 0.0
        return (
            f"{bar}  {percent:3d}%  {done:,}/{self._total:,} rows"
            f"  elapsed {format_duration(elapsed)}"
            f"  ETA {format_duration(remaining)}"
            f"  {rate:,.0f} rows/s"
        )
