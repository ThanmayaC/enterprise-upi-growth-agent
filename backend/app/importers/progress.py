"""Console progress rendering for long-running imports.

Renders a block-style bar that overwrites itself in place::

    --------------------------------------------------
    Importing Transactions
    ██████░░░░  64%
    640,000 / 1,000,000
    --------------------------------------------------

Rendering is throttled so a million-row import does not spend its time
writing to the console: the bar repaints at most every ``min_interval``
seconds or when progress advances a full percentage point.
"""

from __future__ import annotations

import sys
import time

_FULL = "█"   # █
_EMPTY = "░"  # ░


class ProgressBar:
    """A minimal, dependency-free console progress bar."""

    def __init__(self, label: str, total: int, width: int = 10,
                 min_interval: float = 0.5) -> None:
        self.label = label
        self.total = max(total, 1)
        self.width = width
        self.min_interval = min_interval
        self._last_paint = 0.0
        self._last_pct = -1
        sys.stdout.write("-" * 50 + f"\nImporting {label}\n")
        sys.stdout.flush()

    def update(self, done: int) -> None:
        """Repaint the bar if enough progress/time has elapsed."""
        pct = int(done * 100 / self.total)
        now = time.monotonic()
        if pct == self._last_pct and (now - self._last_paint) < self.min_interval:
            return
        self._last_pct = pct
        self._last_paint = now
        filled = int(self.width * done / self.total)
        bar = _FULL * filled + _EMPTY * (self.width - filled)
        sys.stdout.write(f"\r{bar}  {pct:3d}%   {done:,d} / {self.total:,d}")
        sys.stdout.flush()

    def close(self, done: int) -> None:
        """Paint the final state and terminate the bar block."""
        filled = int(self.width * done / self.total)
        bar = _FULL * filled + _EMPTY * (self.width - filled)
        pct = int(done * 100 / self.total)
        sys.stdout.write(
            f"\r{bar}  {pct:3d}%   {done:,d} / {self.total:,d}\n" + "-" * 50 + "\n"
        )
        sys.stdout.flush()
