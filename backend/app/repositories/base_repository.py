"""Generic repository base — shared, reusable database-access machinery.

Purpose:
    Give every repository one implementation of the cross-cutting concerns
    of data access: safe query execution, primary-key lookups, filtering,
    ordering, pagination, and simple aggregates. Concrete repositories
    subclass :class:`BaseRepository`, declare their ``model``, and add only
    the query methods that are meaningful for their table.

Enterprise notes:
    - Repositories receive an externally-managed ``Session`` (constructor
      injection). They never create engines, never commit, and never roll
      back — transaction scope belongs to the caller (a service, a CLI, or
      the ``get_db`` FastAPI dependency). This phase's repositories are
      read-only by design: all writes go through the import pipeline.
    - Every query funnels through the ``_execute_*`` helpers so any driver
      or SQLAlchemy failure surfaces as a single, consistent
      :class:`RepositoryError` — repositories never silently fail.
    - Filter/order column names are validated against the ORM mapping and
      rejected with :class:`InvalidFilterError` before any SQL is emitted,
      so a typo can never become a runtime SQL error (or an injection
      vector).
"""

from __future__ import annotations

import logging
from typing import Any, Generic, Sequence, TypeVar

from sqlalchemy import Select, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import InstrumentedAttribute, Session

from app.db.database import Base

logger = logging.getLogger(__name__)

ModelT = TypeVar("ModelT", bound=Base)

#: Frozen-schema encoding of boolean flags ('Y'/'N' single characters).
#: Shared here so individual repositories never re-declare the literal.
YES_FLAG = "Y"


class RepositoryError(Exception):
    """Base failure of the repository layer (wraps SQLAlchemy errors)."""


class RecordNotFoundError(RepositoryError):
    """A record that was required to exist could not be found."""


class InvalidFilterError(RepositoryError):
    """A filter, ordering, or pagination argument is invalid."""


class BaseRepository(Generic[ModelT]):
    """Reusable, read-only repository for one ORM model.

    Purpose:
        Centralize session handling, validation, and query execution so
        concrete repositories contain nothing but query definitions.

    Parameters:
        session: An open SQLAlchemy ``Session`` owned by the caller.
    """

    #: The ORM model this repository serves; set by every subclass.
    model: type[ModelT]

    def __init__(self, session: Session) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # Generic public API
    # ------------------------------------------------------------------
    def find_by_id(self, record_id: Any) -> ModelT | None:
        """Look up one record by primary key.

        Purpose:
            The cheapest possible single-record access (identity-map aware).

        Parameters:
            record_id: Primary-key value (or tuple for composite keys).

        Returns:
            The entity, or ``None`` when no such record exists.
        """

        try:
            return self._session.get(self.model, record_id)
        except SQLAlchemyError as exc:
            raise self._wrap(exc, f"find_by_id({record_id!r})") from exc

    def get_by_id(self, record_id: Any) -> ModelT:
        """Look up one record by primary key, requiring it to exist.

        Purpose:
            For callers that treat absence as an error condition.

        Parameters:
            record_id: Primary-key value.

        Returns:
            The entity.

        Raises:
            RecordNotFoundError: If no record has this primary key.
        """

        record = self.find_by_id(record_id)
        if record is None:
            raise RecordNotFoundError(
                f"{self.model.__name__} with primary key {record_id!r} does not exist"
            )
        return record

    def find_all(
        self,
        *,
        limit: int | None = None,
        offset: int = 0,
        order_by: str | None = None,
        descending: bool = False,
    ) -> Sequence[ModelT]:
        """Return records with optional ordering and pagination.

        Purpose:
            Generic listing for reference tables and paged access.

        Parameters:
            limit: Maximum rows to return (``None`` = no limit).
            offset: Rows to skip (for pagination).
            order_by: Model attribute name to order on (validated).
            descending: Order direction when ``order_by`` is given.

        Returns:
            The matching entities.
        """

        stmt = self._apply_ordering(select(self.model), order_by, descending)
        stmt = self._apply_pagination(stmt, limit, offset)
        return self._execute_all(stmt)

    def filter_by(
        self,
        *,
        limit: int | None = None,
        offset: int = 0,
        order_by: str | None = None,
        descending: bool = False,
        **criteria: Any,
    ) -> Sequence[ModelT]:
        """Return records matching exact-equality criteria.

        Purpose:
            Ad-hoc filtered access without a bespoke method per column.

        Parameters:
            limit: Maximum rows to return (``None`` = no limit).
            offset: Rows to skip.
            order_by: Model attribute name to order on (validated).
            descending: Order direction when ``order_by`` is given.
            criteria: ``attribute=value`` pairs combined with AND; attribute
                names are validated against the model.

        Returns:
            The matching entities.

        Raises:
            InvalidFilterError: For an unknown attribute name or invalid
                pagination values.
        """

        stmt = select(self.model)
        for name, value in criteria.items():
            stmt = stmt.where(self._column(name) == value)
        stmt = self._apply_ordering(stmt, order_by, descending)
        stmt = self._apply_pagination(stmt, limit, offset)
        return self._execute_all(stmt)

    def count(self) -> int:
        """Count all records of the model.

        Purpose:
            Cheap cardinality checks and reporting.

        Returns:
            The total row count.
        """

        stmt = select(func.count()).select_from(self.model)
        return int(self._execute_scalar(stmt) or 0)

    def exists(self, record_id: Any) -> bool:
        """Check whether a record with the given primary key exists.

        Purpose:
            Existence probes without materializing the entity.

        Parameters:
            record_id: Primary-key value.

        Returns:
            ``True`` if the record exists.
        """

        pk_columns = list(self.model.__table__.primary_key.columns)
        values = record_id if isinstance(record_id, tuple) else (record_id,)
        if len(values) != len(pk_columns):
            raise InvalidFilterError(
                f"{self.model.__name__} primary key takes {len(pk_columns)} "
                f"value(s), got {len(values)}"
            )
        stmt = select(1)
        for column, value in zip(pk_columns, values):
            stmt = stmt.where(column == value)
        return self._execute_scalar(stmt.limit(1)) is not None

    # ------------------------------------------------------------------
    # Composable building blocks for subclasses
    # ------------------------------------------------------------------
    def _column(self, name: str) -> InstrumentedAttribute[Any]:
        """Resolve a model attribute name to its mapped column, or reject it."""

        attr = getattr(self.model, name, None)
        if not isinstance(attr, InstrumentedAttribute):
            raise InvalidFilterError(
                f"'{name}' is not a mapped attribute of {self.model.__name__}"
            )
        return attr

    def _apply_ordering(
        self, stmt: Select[Any], order_by: str | None, descending: bool
    ) -> Select[Any]:
        """Apply validated ordering to a statement (no-op when unset)."""

        if order_by is None:
            return stmt
        column = self._column(order_by)
        return stmt.order_by(column.desc() if descending else column.asc())

    @staticmethod
    def _apply_pagination(
        stmt: Select[Any], limit: int | None, offset: int
    ) -> Select[Any]:
        """Apply validated limit/offset to a statement."""

        if limit is not None:
            if limit < 0:
                raise InvalidFilterError(f"limit must be >= 0, got {limit}")
            stmt = stmt.limit(limit)
        if offset:
            if offset < 0:
                raise InvalidFilterError(f"offset must be >= 0, got {offset}")
            stmt = stmt.offset(offset)
        return stmt

    # ------------------------------------------------------------------
    # Safe execution — the single choke point for database errors
    # ------------------------------------------------------------------
    def _execute_all(self, stmt: Select[Any]) -> Sequence[ModelT]:
        """Execute a statement returning entities; wrap driver failures."""

        try:
            return self._session.scalars(stmt).all()
        except SQLAlchemyError as exc:
            raise self._wrap(exc, "list query") from exc

    def _execute_one_or_none(self, stmt: Select[Any]) -> ModelT | None:
        """Execute a statement expected to return at most one entity."""

        try:
            return self._session.scalars(stmt).one_or_none()
        except SQLAlchemyError as exc:
            raise self._wrap(exc, "single-row query") from exc

    def _execute_scalar(self, stmt: Select[Any]) -> Any:
        """Execute a statement returning one scalar value (or ``None``)."""

        try:
            return self._session.execute(stmt).scalar()
        except SQLAlchemyError as exc:
            raise self._wrap(exc, "scalar query") from exc

    def _execute_rows(self, stmt: Select[Any]) -> Sequence[Any]:
        """Execute a statement returning plain result rows (aggregates)."""

        try:
            return self._session.execute(stmt).all()
        except SQLAlchemyError as exc:
            raise self._wrap(exc, "row query") from exc

    def _wrap(self, exc: SQLAlchemyError, operation: str) -> RepositoryError:
        """Build the consistent repository-layer exception for a failure."""

        reason = str(getattr(exc, "orig", exc)).splitlines()[0][:200]
        logger.error("%s %s failed: %s", self.model.__name__, operation, reason)
        return RepositoryError(
            f"{self.model.__name__} {operation} failed: {reason}"
        )
