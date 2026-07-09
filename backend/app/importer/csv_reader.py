"""CSV Reader — the streaming source layer of the import pipeline.

Purpose:
    Provide memory-safe, generator-based access to CSV sources. This layer
    knows *nothing* about the database or the ORM — it only understands
    files, encodings, and headers, so the same reader serves every dataset.

Enterprise notes:
    - Rows are streamed one at a time through :func:`read_csv`; the file is
      never materialized in memory, which is what allows the pipeline to
      handle multi-million-row fact files.
    - Files are opened as ``utf-8-sig`` so a UTF-8 byte-order mark (common
      when CSVs pass through Windows tooling) never corrupts the first
      header cell.
    - The header is validated *structurally* here (present, non-blank, no
      duplicate cells). Semantic validation against the ORM schema is the
      responsibility of the Validation Layer.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterator

#: ``csv.DictReader`` key under which values beyond the header width are
#: collected. Its presence in a row marks the row as malformed (too many
#: fields); the Validation Layer rejects such rows.
EXTRA_FIELDS_KEY = "__extra_fields__"

#: Chunk size (bytes) used when counting rows without parsing them.
_COUNT_CHUNK_BYTES = 1 << 20


class CsvReadError(Exception):
    """Raised when a CSV source cannot be opened or its header is unusable."""


def read_header(path: Path) -> list[str]:
    """Read and structurally validate the header row of a CSV file.

    Purpose:
        Fail fast — callers can verify a source is well-formed before any
        streaming, database work, or progress display begins.

    Parameters:
        path: Location of the CSV file.

    Returns:
        The header cells in file order.

    Raises:
        CsvReadError: If the file is missing, empty, or the header contains
            blank or duplicated column names.
    """

    if not path.is_file():
        raise CsvReadError(f"CSV file not found: {path}")

    with path.open(newline="", encoding="utf-8-sig") as handle:
        try:
            header = next(csv.reader(handle))
        except StopIteration:
            raise CsvReadError(f"CSV file is empty (no header row): {path}") from None

    if not header or all(cell.strip() == "" for cell in header):
        raise CsvReadError(f"CSV header row is blank: {path}")

    blank = [i + 1 for i, cell in enumerate(header) if cell.strip() == ""]
    if blank:
        raise CsvReadError(
            f"CSV header contains blank column names at positions {blank}: {path}"
        )

    duplicates = sorted({cell for cell in header if header.count(cell) > 1})
    if duplicates:
        raise CsvReadError(
            f"CSV header contains duplicated column names {duplicates}: {path}"
        )

    return header


def read_csv(path: Path) -> Iterator[dict[str, str | None]]:
    """Stream a CSV file row by row as dictionaries keyed by header name.

    Purpose:
        The single streaming entry point of the pipeline. Yields one row at
        a time so memory usage is constant regardless of file size.

    Parameters:
        path: Location of the CSV file. The header is validated (via
            :func:`read_header`) before the first row is yielded.

    Returns:
        A generator of ``{column_name: value}`` dictionaries. A value of
        ``None`` means the physical row had *fewer* fields than the header;
        surplus fields are collected under :data:`EXTRA_FIELDS_KEY`. Both
        conditions are flagged as malformed rows by the Validation Layer.

    Raises:
        CsvReadError: If the file or its header is unusable.
    """

    read_header(path)  # fail fast before any row is produced

    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle, restkey=EXTRA_FIELDS_KEY, restval=None)
        yield from reader


def count_data_rows(path: Path) -> int:
    """Count the data rows of a CSV file without parsing it.

    Purpose:
        Supplies the *total* used by the progress tracker (percentage / ETA).
        Counting scans the file in binary chunks, so a half-gigabyte fact
        file is counted in seconds with constant memory.

    Parameters:
        path: Location of the CSV file.

    Returns:
        The number of newline-terminated rows minus the header. This is an
        estimate for display purposes only (quoted embedded newlines would
        overcount); authoritative row counts come from the import itself.
    """

    newlines = 0
    with path.open("rb") as handle:
        while chunk := handle.read(_COUNT_CHUNK_BYTES):
            newlines += chunk.count(b"\n")
    return max(newlines - 1, 0)
