"""Pre-import validation for CSV sources.

Each importer runs these checks *before* touching the database so that a
bad file fails fast with a precise, actionable message instead of a
half-completed load:

    - file exists and is a file
    - file is not empty (has a header and at least one data row)
    - header exactly matches the ORM table's column set (no missing
      required columns, no unknown columns)
    - duplicate primary keys inside the CSV (masters are checked up front;
      the streaming transaction importer deduplicates on the fly)
"""

from __future__ import annotations

import csv
from pathlib import Path

from sqlalchemy import Table


class CsvValidationError(Exception):
    """Raised when a CSV source fails pre-import validation."""


def validate_csv_source(path: Path, table: Table) -> list[str]:
    """Validate file presence, non-emptiness, and header ↔ ORM agreement.

    Returns the CSV header (column order as found in the file). Raises
    :class:`CsvValidationError` with a meaningful message on any failure.
    """

    if not path.exists() or not path.is_file():
        raise CsvValidationError(f"CSV file not found: {path}")

    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        try:
            header = next(reader)
        except StopIteration:
            raise CsvValidationError(f"CSV file is empty (no header): {path}")

        try:
            next(reader)
        except StopIteration:
            raise CsvValidationError(f"CSV file has no data rows: {path}")

    expected = {c.name for c in table.columns}
    found = set(header)

    missing = sorted(expected - found)
    unknown = sorted(found - expected)
    if missing or unknown:
        raise CsvValidationError(
            f"Header mismatch for table '{table.name}' in {path.name}: "
            f"missing columns {missing or 'none'}; "
            f"unknown columns {unknown or 'none'}"
        )
    if len(header) != len(found):
        dupes = sorted({h for h in header if header.count(h) > 1})
        raise CsvValidationError(
            f"Duplicated header columns in {path.name}: {dupes}"
        )

    return header


def find_duplicate_pks(rows: list[dict[str, str]], pk_columns: list[str]) -> list[tuple]:
    """Return the primary-key values that occur more than once in ``rows``.

    Used for the in-memory master imports; the transaction importer performs
    the same check incrementally while streaming.
    """

    seen: set[tuple] = set()
    duplicates: list[tuple] = []
    for row in rows:
        key = tuple(row[c] for c in pk_columns)
        if key in seen:
            duplicates.append(key)
        else:
            seen.add(key)
    return duplicates
