"""Validation Layer — structural and type validation of CSV rows.

Purpose:
    Decide, for every CSV row, whether it can safely become a database row —
    *before* any transformation or database work happens. All checks are
    derived from the frozen ORM schema (``Table`` metadata), so the layer
    never hard-codes column lists and automatically stays consistent with
    the models.

Checks performed:
    - header: missing required columns / unexpected columns
    - malformed rows (more or fewer fields than the header)
    - empty primary key values
    - duplicate primary keys (streaming, incremental)
    - unexpected NULL/empty values in NOT NULL columns
    - invalid decimal, integer, date, timestamp, and UUID values
    - string values exceeding the declared column length

Enterprise notes:
    - This layer performs **no database operations** and never mutates the
      row; it only reports :class:`ValidationIssue` objects, leaving the
      caller in full control of rejection policy.
    - Duplicate-key detection keeps one key per row in memory (a plain
      string for single-column keys). Correctness is preferred over the
      smaller footprint of hashing, which could silently reject good rows
      on a hash collision.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Callable
from uuid import UUID

from sqlalchemy import Date, DateTime, Integer, Numeric, String, Table, Uuid

from app.importer.csv_reader import EXTRA_FIELDS_KEY

#: A checker takes a non-empty, stripped string and returns a failure
#: reason, or ``None`` when the value is acceptable.
Checker = Callable[[str], str | None]

#: Column name used for issues affecting the row as a whole.
WHOLE_ROW = "*"


@dataclass(frozen=True)
class ValidationIssue:
    """One structured validation failure.

    Attributes:
        row_number: 1-based data-row number (header excluded); ``0`` for
            header-level issues.
        column: Offending column name, or :data:`WHOLE_ROW` for whole-row
            problems such as malformed field counts.
        value: The offending raw value (``None`` for missing fields).
        reason: Human-readable explanation of the failure.
    """

    row_number: int
    column: str
    value: str | None
    reason: str


def validate_header(header: list[str], table: Table) -> list[ValidationIssue]:
    """Compare a CSV header against the ORM table's column set.

    Purpose:
        Guarantee schema agreement before a single row is processed: a
        renamed or missing column must abort the dataset, not poison it.

    Parameters:
        header: Header cells as returned by the CSV Reader.
        table: SQLAlchemy ``Table`` the CSV feeds.

    Returns:
        A list of :class:`ValidationIssue` (empty when the header exactly
        matches the table's column names, in any order).
    """

    expected = {column.name for column in table.columns}
    found = set(header)

    issues: list[ValidationIssue] = []
    for name in sorted(expected - found):
        issues.append(
            ValidationIssue(0, name, None, f"required column '{name}' missing from CSV header")
        )
    for name in sorted(found - expected):
        issues.append(
            ValidationIssue(
                0, name, None,
                f"unexpected column '{name}' not present on table '{table.name}'",
            )
        )
    return issues


def _check_decimal(value: str) -> str | None:
    try:
        Decimal(value)
    except InvalidOperation:
        return "invalid decimal value"
    return None


def _check_integer(value: str) -> str | None:
    try:
        int(value)
    except ValueError:
        return "invalid integer value"
    return None


def _check_date(value: str) -> str | None:
    try:
        date.fromisoformat(value)
    except ValueError:
        return "invalid date (expected YYYY-MM-DD)"
    return None


def _check_datetime(value: str) -> str | None:
    try:
        datetime.fromisoformat(value)
    except ValueError:
        return "invalid timestamp (expected YYYY-MM-DD HH:MM:SS)"
    return None


def _check_uuid(value: str) -> str | None:
    try:
        UUID(value)
    except ValueError:
        return "invalid UUID value"
    return None


def _make_length_checker(limit: int) -> Checker:
    def check(value: str) -> str | None:
        if len(value) > limit:
            return f"length {len(value)} exceeds column limit {limit}"
        return None

    return check


def _checker_for(column) -> Checker | None:
    """Pick the value checker matching a column's SQLAlchemy type."""

    column_type = column.type
    if isinstance(column_type, Uuid):
        return _check_uuid
    if isinstance(column_type, DateTime):
        return _check_datetime
    if isinstance(column_type, Date):
        return _check_date
    if isinstance(column_type, Numeric):
        return _check_decimal
    if isinstance(column_type, Integer):
        return _check_integer
    if isinstance(column_type, String) and column_type.length is not None:
        return _make_length_checker(column_type.length)
    return None


class RowValidator:
    """Streaming, schema-driven validator for the rows of one table.

    Purpose:
        Validate rows one at a time while the CSV streams past, including
        incremental duplicate-primary-key detection — no full-file pass is
        ever required.

    Parameters:
        table: SQLAlchemy ``Table`` whose column types and primary key
            drive every check.
    """

    def __init__(self, table: Table) -> None:
        self._columns: list[tuple[str, bool, Checker | None]] = [
            (column.name, bool(column.nullable), _checker_for(column))
            for column in table.columns
        ]
        self._pk_columns: list[str] = [c.name for c in table.primary_key.columns]
        self._single_pk: bool = len(self._pk_columns) == 1
        self._seen_keys: set[str | tuple[str, ...]] = set()

    def validate_row(
        self, row: dict[str, str | None], row_number: int
    ) -> list[ValidationIssue]:
        """Validate one CSV row against the table schema.

        Purpose:
            Produce the complete set of problems for a row so a reject
            record explains *everything* wrong with it, not just the first
            failure.

        Parameters:
            row: Raw row dictionary from the CSV Reader (values are strings,
                or ``None`` for missing fields).
            row_number: 1-based data-row number, used in issue reports.

        Returns:
            A list of :class:`ValidationIssue`; empty when the row is valid.
        """

        issues: list[ValidationIssue] = []

        if EXTRA_FIELDS_KEY in row:
            issues.append(
                ValidationIssue(
                    row_number, WHOLE_ROW, None,
                    "malformed row: more fields than header columns",
                )
            )

        for name, nullable, checker in self._columns:
            raw = row.get(name)
            if raw is None:
                issues.append(
                    ValidationIssue(
                        row_number, name, None,
                        "malformed row: fewer fields than header columns",
                    )
                )
                continue
            value = raw.strip()
            if value == "":
                if not nullable:
                    issues.append(
                        ValidationIssue(
                            row_number, name, raw,
                            "unexpected NULL: empty value in NOT NULL column",
                        )
                    )
                continue
            if checker is not None:
                reason = checker(value)
                if reason is not None:
                    issues.append(ValidationIssue(row_number, name, raw, reason))

        issues.extend(self._validate_primary_key(row, row_number))
        return issues

    def _validate_primary_key(
        self, row: dict[str, str | None], row_number: int
    ) -> list[ValidationIssue]:
        """Check the row's primary key for emptiness and duplication."""

        parts = tuple((row.get(name) or "").strip() for name in self._pk_columns)
        if any(part == "" for part in parts):
            return [
                ValidationIssue(
                    row_number, ", ".join(self._pk_columns), None,
                    "empty primary key value",
                )
            ]

        key: str | tuple[str, ...] = parts[0] if self._single_pk else parts
        if key in self._seen_keys:
            return [
                ValidationIssue(
                    row_number, ", ".join(self._pk_columns), str(key),
                    "duplicate primary key within CSV",
                )
            ]
        self._seen_keys.add(key)
        return []
