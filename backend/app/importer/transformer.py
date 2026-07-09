"""Transformation Layer — CSV strings to ORM-compatible Python values.

Purpose:
    Convert one validated CSV row into a dictionary ready for a bulk
    INSERT: exact ``Decimal`` for money, real ``datetime``/``date`` objects,
    ``UUID`` instances, trimmed strings, and ``None`` for empty nullable
    values. Converters are derived from the frozen ORM schema, so the layer
    never hard-codes column lists.

Enterprise notes:
    - This layer performs **no inserts, no commits, and no SQL** — it is a
      pure function of its input row.
    - Money is always ``Decimal``; floats are never produced.
    - The Validation Layer runs first, so conversion failures here are
      unexpected — but they still raise a precise :class:`RowTransformError`
      (never silently corrupting data) and the caller rejects the row.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Callable
from uuid import UUID

from sqlalchemy import Date, DateTime, Integer, Numeric, Table, Uuid

#: A converter takes a non-empty, stripped string and returns the typed
#: Python value expected by the ORM column.
Converter = Callable[[str], Any]


class RowTransformError(Exception):
    """Raised when a CSV value cannot be converted to its column type.

    Attributes:
        column: Name of the offending column.
        value: The raw offending value.
        reason: Human-readable explanation of the failure.
    """

    def __init__(self, column: str, value: str | None, reason: str) -> None:
        self.column = column
        self.value = value
        self.reason = reason
        super().__init__(f"column '{column}': {reason} (value: {value!r})")


def _to_decimal(value: str) -> Decimal:
    try:
        return Decimal(value)
    except InvalidOperation as exc:  # Decimal raises outside ValueError
        raise ValueError(f"invalid decimal value: {value!r}") from exc


def _converter_for(column) -> Converter:
    """Pick the string-to-value converter matching a column's type."""

    column_type = column.type
    if isinstance(column_type, Uuid):
        return UUID
    if isinstance(column_type, DateTime):
        return datetime.fromisoformat
    if isinstance(column_type, Date):
        return date.fromisoformat
    if isinstance(column_type, Numeric):
        return _to_decimal
    if isinstance(column_type, Integer):
        return int
    return str  # value is already a stripped string


class RowTransformer:
    """Schema-driven transformer for the rows of one table.

    Purpose:
        Build the per-column converter map once, then convert rows at
        streaming speed with a single dictionary construction per row.

    Parameters:
        table: SQLAlchemy ``Table`` whose column types drive conversion.
    """

    def __init__(self, table: Table) -> None:
        self._columns: list[tuple[str, bool, Converter]] = [
            (column.name, bool(column.nullable), _converter_for(column))
            for column in table.columns
        ]

    def transform(self, row: dict[str, str | None]) -> dict[str, Any]:
        """Convert one CSV row into an ORM-compatible dictionary.

        Purpose:
            Produce the exact ``{db_column: typed_value}`` mapping consumed
            by the Batch Processing Layer's bulk INSERT.

        Parameters:
            row: Raw row dictionary from the CSV Reader; values are trimmed
                here, and empty strings become ``None`` for nullable columns.

        Returns:
            A dictionary keyed by database column name with typed values.

        Raises:
            RowTransformError: If a value cannot be converted or a NOT NULL
                column is empty (defence in depth behind the validator).
        """

        out: dict[str, Any] = {}
        for name, nullable, convert in self._columns:
            raw = row.get(name)
            value = raw.strip() if raw is not None else ""
            if value == "":
                if not nullable:
                    raise RowTransformError(name, raw, "empty value for NOT NULL column")
                out[name] = None
                continue
            try:
                out[name] = convert(value)
            except (ValueError, TypeError) as exc:
                raise RowTransformError(name, raw, str(exc)) from exc
        return out
