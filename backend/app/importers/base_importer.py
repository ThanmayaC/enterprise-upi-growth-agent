"""Template-method base class for all CSV importers.

One importer = one CSV = one table. The lifecycle is fixed here so every
import behaves identically:

    validate source  →  (optionally) guard against re-import
    →  stream + transform + deduplicate  →  batched ORM inserts
    →  per-batch commit / rollback  →  ImportResult

Loading strategy:
    - Rows are inserted with SQLAlchemy's ORM-session bulk INSERT
      (``session.execute(insert(table), [rows...])``) which uses the
      2.x *insertmanyvalues* fast path — never row-by-row.
    - Commits happen per batch (configurable). A failing batch is rolled
      back and recorded; subsequent batches continue, so one poison batch
      cannot destroy an entire load.
    - Rejected rows (validation/transform failures, duplicate PKs) are
      appended to a reject file with their reason — data is never lost
      silently.
"""

from __future__ import annotations

import csv
import time
from pathlib import Path
from typing import Any, Iterator

from sqlalchemy import Table, delete, func, insert, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.db.database import Base
from app.importers.progress import ProgressBar
from app.importers.report import ImportResult
from app.importers.transformers import RowTransformError, build_row_transformer
from app.importers.validators import CsvValidationError, validate_csv_source


class BaseImporter:
    """Reusable importer for one CSV → one ORM-mapped table."""

    #: rows per INSERT batch / commit — subclasses tune this for their volume
    batch_size: int = 5_000

    def __init__(self, name: str, model: type[Base], csv_path: Path,
                 reject_dir: Path, batch_size: int | None = None) -> None:
        self.name = name
        self.model = model
        self.table: Table = model.__table__
        self.csv_path = csv_path
        self.reject_dir = reject_dir
        if batch_size is not None:
            self.batch_size = batch_size
        self._reject_handle = None
        self._reject_writer = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def run(self, session_factory: sessionmaker[Session], reset: bool = False) -> ImportResult:
        """Execute the full import lifecycle and return its result."""

        result = ImportResult(name=self.name, table=self.table.name,
                              csv_path=str(self.csv_path))
        started = time.monotonic()
        try:
            header = validate_csv_source(self.csv_path, self.table)
            result.csv_rows = self._count_data_rows()

            with session_factory() as session:
                existing = session.execute(
                    select(func.count()).select_from(self.table)
                ).scalar_one()
                if existing and not reset:
                    result.status = "SKIPPED"
                    result.messages.append(
                        f"table already holds {existing:,d} rows — rerun with "
                        f"--reset to reload"
                    )
                    return result
                if existing and reset:
                    session.execute(delete(self.table))
                    session.commit()
                    result.messages.append(f"reset: removed {existing:,d} existing rows")

            self._load(session_factory, header, result)

            if result.failed_batches or (result.inserted == 0 and result.csv_rows > 0):
                result.status = "FAIL"
            else:
                result.status = "PASS"
        except CsvValidationError as exc:
            result.status = "FAIL"
            result.messages.append(str(exc))
        finally:
            result.duration_seconds = time.monotonic() - started
            self._close_rejects()
        return result

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------
    def _load(self, session_factory: sessionmaker[Session], header: list[str],
              result: ImportResult) -> None:
        transform = build_row_transformer(self.table)
        pk_columns = [c.name for c in self.table.primary_key.columns]
        seen_pks: set[tuple] = set()

        bar = ProgressBar(self.name, total=result.csv_rows)
        batch: list[dict[str, Any]] = []
        processed = 0

        with session_factory() as session:
            for row in self._stream_rows():
                processed += 1

                key = tuple(row[c] for c in pk_columns)
                if key in seen_pks:
                    self._reject(header, row, f"duplicate primary key {key}")
                    result.rejected += 1
                    continue
                seen_pks.add(key)

                try:
                    batch.append(transform(row))
                except RowTransformError as exc:
                    self._reject(header, row, str(exc))
                    result.rejected += 1
                    continue

                if len(batch) >= self.batch_size:
                    self._flush(session, batch, result)
                    batch = []
                    bar.update(processed)

            if batch:
                self._flush(session, batch, result)
        bar.close(processed)

    def _flush(self, session: Session, batch: list[dict[str, Any]],
               result: ImportResult) -> None:
        """Insert one batch; commit it, or roll back only this batch."""
        try:
            session.execute(insert(self.table), batch)
            session.commit()
            result.inserted += len(batch)
        except SQLAlchemyError as exc:
            session.rollback()
            result.failed_batches += 1
            reason = str(getattr(exc, "orig", exc)).splitlines()[0][:200]
            result.messages.append(
                f"batch of {len(batch):,d} rows rolled back: {reason}"
            )

    # ------------------------------------------------------------------
    # CSV streaming helpers
    # ------------------------------------------------------------------
    def _stream_rows(self) -> Iterator[dict[str, str]]:
        with self.csv_path.open(newline="", encoding="utf-8") as handle:
            yield from csv.DictReader(handle)

    def _count_data_rows(self) -> int:
        with self.csv_path.open(newline="", encoding="utf-8") as handle:
            return max(sum(1 for _ in handle) - 1, 0)

    # ------------------------------------------------------------------
    # Reject capture — rejected rows are persisted, never dropped silently
    # ------------------------------------------------------------------
    def _reject(self, header: list[str], row: dict[str, str], reason: str) -> None:
        if self._reject_writer is None:
            self.reject_dir.mkdir(parents=True, exist_ok=True)
            path = self.reject_dir / f"rejects_{self.table.name}.csv"
            self._reject_handle = path.open("w", newline="", encoding="utf-8")
            self._reject_writer = csv.writer(self._reject_handle)
            self._reject_writer.writerow(header + ["__reject_reason__"])
        self._reject_writer.writerow([row[h] for h in header] + [reason])

    def _close_rejects(self) -> None:
        if self._reject_handle is not None:
            self._reject_handle.close()
            self._reject_handle = None
            self._reject_writer = None
