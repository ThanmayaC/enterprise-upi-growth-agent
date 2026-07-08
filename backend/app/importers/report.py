"""Import result model and enterprise report rendering.

Every importer returns an :class:`ImportResult`; the loader aggregates them
into the final Enterprise Import Report and the post-import verification
summary. Rendering is plain text so the report reads identically in a
terminal, a log file, or a CI console.
"""

from __future__ import annotations

from dataclasses import dataclass, field

RULE = "=" * 62
LINE = "-" * 62


@dataclass
class ImportResult:
    """Outcome of one CSV import (one table)."""

    name: str                 # human label, e.g. "Customer Master"
    table: str                # target database table
    csv_path: str             # source file
    status: str = "PENDING"   # PASS / FAIL / SKIPPED
    csv_rows: int = 0         # data rows found in the CSV
    inserted: int = 0         # rows committed to the database
    rejected: int = 0         # rows rejected by validation/transformation
    failed_batches: int = 0   # batches rolled back
    duration_seconds: float = 0.0
    messages: list[str] = field(default_factory=list)


def render_report(
    results: list[ImportResult],
    total_duration_seconds: float,
    database_status: str,
) -> str:
    """Render the final Enterprise Import Report as plain text."""

    lines: list[str] = [RULE, "Enterprise Import Report".center(62), RULE]

    for r in results:
        lines.append(f"{r.name:<28s} {r.status:<8s} {r.inserted:>10,d} rows"
                     f"   ({r.duration_seconds:.1f}s)")
        if r.rejected:
            lines.append(f"{'':28s} rejected: {r.rejected:,d}")
        if r.failed_batches:
            lines.append(f"{'':28s} failed batches: {r.failed_batches}")
        for msg in r.messages:
            lines.append(f"{'':28s} note: {msg}")

    total_inserted = sum(r.inserted for r in results)
    total_rejected = sum(r.rejected for r in results)
    total_failed = sum(r.failed_batches for r in results)

    lines += [
        LINE,
        f"{'Total Rows Inserted':<28s} {total_inserted:>18,d}",
        f"{'Rejected Rows':<28s} {total_rejected:>18,d}",
        f"{'Failed Batches':<28s} {total_failed:>18,d}",
        f"{'Import Duration':<28s} {total_duration_seconds:>16.1f} s",
        f"{'Database Status':<28s} {database_status:>18s}",
        RULE,
    ]
    return "\n".join(lines)


def render_verification(rows: list[tuple[str, str, str]]) -> str:
    """Render the post-import verification summary.

    ``rows`` is a list of (check, target, outcome) tuples.
    """

    lines = [RULE, "Post-Import Verification".center(62), RULE]
    for check, target, outcome in rows:
        lines.append(f"{check:<26s} {target:<26s} {outcome}")
    lines.append(RULE)
    return "\n".join(lines)
