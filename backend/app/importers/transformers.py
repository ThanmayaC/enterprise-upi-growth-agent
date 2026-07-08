"""Type-safe transformation of CSV strings into database-ready values.

The transformer is *derived from the frozen ORM schema*: for each table a
converter is built per column based on its SQLAlchemy type, so the import
engine never hard-codes column lists and automatically stays consistent
with the models.

Conversion rules (nothing is ever lost silently):
    - ``''``            → ``NULL`` for nullable columns; for a NOT NULL
                          column an empty value **rejects the row** with a
                          precise reason.
    - ``Date``          → ``datetime.date`` (ISO ``YYYY-MM-DD``)
    - ``DateTime``      → ``datetime.datetime`` (``YYYY-MM-DD HH:MM:SS``)
    - ``Numeric``       → ``decimal.Decimal`` (money is never float)
    - ``Integer``       → ``int``
    - ``Uuid/UUID``     → ``uuid.UUID`` (no such column exists in the frozen
                          schema today; supported for completeness)
    - ``String/Text``   → stripped-verbatim string. Y/N flags are stored as
                          their dataset encoding per the frozen schema — the
                          schema owns fidelity, consumers own conversion.
    - overlong strings  → **reject** (never truncate data silently)
Any conversion failure raises :class:`RowTransformError` naming the column,
the offending value, and the reason.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Callable

from sqlalchemy import Date, DateTime, Integer, Numeric, String, Table, Uuid

Converter = Callable[[str], Any]


class RowTransformError(Exception):
    """Raised when a CSV row cannot be converted to database values."""

    def __init__(self, column: str, value: str, reason: str) -> None:
        self.column = column
        self.value = value
        self.reason = reason
        super().__init__(f"column '{column}': {reason} (value: {value!r})")


def _to_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def _to_datetime(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")


def _to_decimal(value: str) -> Decimal:
    try:
        return Decimal(value)
    except InvalidOperation as exc:  # Decimal raises its own hierarchy
        raise ValueError(str(exc)) from exc


def _to_int(value: str) -> int:
    return int(value)


def _to_uuid(value: str) -> uuid.UUID:
    return uuid.UUID(value)


def _converter_for(column) -> Converter:
    """Pick the CSV-string converter matching a column's SQLAlchemy type."""

    ctype = column.type
    if isinstance(ctype, Uuid):          # covers UUID as well (subclass)
        return _to_uuid
    if isinstance(ctype, DateTime):      # check before Date (no overlap, but explicit)
        return _to_datetime
    if isinstance(ctype, Date):
        return _to_date
    if isinstance(ctype, Numeric):
        return _to_decimal
    if isinstance(ctype, Integer):
        return _to_int

    # String/Text: enforce declared length — reject rather than truncate.
    max_len = getattr(ctype, "length", None)
    if isinstance(ctype, String) and max_len is not None:
        def _to_bounded_str(value: str, _max: int = max_len) -> str:
            if len(value) > _max:
                raise ValueError(f"length {len(value)} exceeds column limit {_max}")
            return value
        return _to_bounded_str

    return lambda value: value


def build_row_transformer(table: Table) -> Callable[[dict[str, str]], dict[str, Any]]:
    """Build a transformer converting one CSV row dict for ``table``.

    The returned callable maps CSV strings (keyed by database column name)
    to typed values ready for an INSERT, raising :class:`RowTransformError`
    on the first unconvertible or contract-violating value.
    """

    converters: dict[str, tuple[Converter, bool]] = {
        col.name: (_converter_for(col), col.nullable) for col in table.columns
    }

    def transform(row: dict[str, str]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for name, (convert, nullable) in converters.items():
            raw = row[name].strip()
            if raw == "":
                if not nullable:
                    raise RowTransformError(name, raw, "empty value for NOT NULL column")
                out[name] = None
                continue
            try:
                out[name] = convert(raw)
            except (ValueError, TypeError) as exc:
                raise RowTransformError(name, raw, str(exc)) from exc
        return out

    return transform
