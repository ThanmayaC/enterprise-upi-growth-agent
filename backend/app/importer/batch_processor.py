"""Batch Processing Layer — bulk, transactional loading of transformed rows.

Purpose:
    Consume an iterable of ORM-compatible row dictionaries and write them to
    PostgreSQL in fixed-size batches. This is the only layer of the pipeline
    that touches the database.

Enterprise notes:
    - Rows are inserted with SQLAlchemy 2.x Core ``insert()`` executemany
      (the *insertmanyvalues* fast path) — never row-by-row ORM adds.
    - Each batch is committed independently. A failing batch is rolled back,
      recorded, and logged; the remaining batches continue, so one poison
      batch cannot destroy a multi-million-row load.
    - The input is consumed lazily: combined with the streaming CSV Reader,
      at most one batch of rows is ever held in memory.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable

from sqlalchemy import Table, insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

logger = logging.getLogger(__name__)

#: Enterprise default batch size — large enough to amortize commit
#: overhead, small enough to bound memory and rollback scope.
DEFAULT_BATCH_SIZE = 5_000

#: Callback invoked after every batch with the cumulative number of rows
#: consumed so far (inserted + rows in failed batches).
ProgressCallback = Callable[[int], None]


@dataclass
class BatchStats:
    """Outcome of one batched load.

    Attributes:
        inserted: Rows committed to the database.
        failed_rows: Rows lost to rolled-back batches.
        committed_batches: Batches committed successfully.
        failed_batches: Batches rolled back after a database error.
        batch_errors: One condensed reason per failed batch.
    """

    inserted: int = 0
    failed_rows: int = 0
    committed_batches: int = 0
    failed_batches: int = 0
    batch_errors: list[str] = field(default_factory=list)


class BatchProcessor:
    """Configurable bulk loader with per-batch commit/rollback isolation.

    Purpose:
        Own the database write path of the pipeline: batching, bulk INSERT,
        transaction boundaries, failure isolation, and progress reporting.

    Parameters:
        session_factory: The application's ``SessionLocal`` (or a compatible
            ``sessionmaker``); one session is used per :meth:`process` call.
        batch_size: Rows per INSERT/commit; defaults to
            :data:`DEFAULT_BATCH_SIZE`.
        on_progress: Optional callback receiving the cumulative row count
            after each batch — used by the orchestrator to drive the
            progress display.
    """

    def __init__(
        self,
        session_factory: sessionmaker[Session],
        batch_size: int = DEFAULT_BATCH_SIZE,
        on_progress: ProgressCallback | None = None,
    ) -> None:
        if batch_size < 1:
            raise ValueError(f"batch_size must be a positive integer, got {batch_size}")
        self._session_factory = session_factory
        self._batch_size = batch_size
        self._on_progress = on_progress

    def process(self, table: Table, rows: Iterable[dict[str, Any]]) -> BatchStats:
        """Load an iterable of transformed rows into ``table`` in batches.

        Purpose:
            The single write entry point: accumulate rows to the configured
            batch size, bulk-insert, commit; on failure roll back only the
            current batch and continue.

        Parameters:
            table: Target SQLAlchemy ``Table``.
            rows: Iterable (typically a generator) of ``{column: value}``
                dictionaries produced by the Transformation Layer.

        Returns:
            A :class:`BatchStats` describing the load.
        """

        stats = BatchStats()
        batch: list[dict[str, Any]] = []

        with self._session_factory() as session:
            for row in rows:
                batch.append(row)
                if len(batch) >= self._batch_size:
                    self._flush(session, table, batch, stats)
                    batch = []
            if batch:
                self._flush(session, table, batch, stats)

        return stats

    def _flush(
        self,
        session: Session,
        table: Table,
        batch: list[dict[str, Any]],
        stats: BatchStats,
    ) -> None:
        """Insert one batch and commit it, or roll back only this batch."""

        batch_number = stats.committed_batches + stats.failed_batches + 1
        logger.debug(
            "Writing batch %d (%s rows) to '%s' ...",
            batch_number, f"{len(batch):,}", table.name,
        )
        try:
            session.execute(insert(table), batch)
            session.commit()
            stats.inserted += len(batch)
            stats.committed_batches += 1
        except SQLAlchemyError as exc:
            session.rollback()
            stats.failed_batches += 1
            stats.failed_rows += len(batch)
            reason = str(getattr(exc, "orig", exc)).splitlines()[0][:200]
            stats.batch_errors.append(f"batch {batch_number}: {reason}")
            logger.warning(
                "Batch %d (%s rows) into '%s' rolled back: %s",
                batch_number, f"{len(batch):,}", table.name, reason,
            )

        if self._on_progress is not None:
            self._on_progress(stats.inserted + stats.failed_rows)
