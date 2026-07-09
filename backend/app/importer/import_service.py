"""Import Service — orchestration of the full enterprise CSV import.

Purpose:
    Drive the entire pipeline in the frozen dependency order (the 11 master
    tables first, the transaction fact last), wiring together the CSV
    Reader, Validation, Transformation, and Batch Processing layers, the
    progress display, per-dataset statistics, and the final summary.

Enterprise notes:
    - Import order is fixed by :func:`build_dataset_specs`; the transaction
      fact is additionally *blocked* if any master import fails outright, so
      fact data can never land ahead of (or without) its reference data.
    - Each dataset is idempotency-guarded: a table that already holds rows
      is skipped unless the run was started with ``reset=True``, which
      deletes existing rows first.
    - Rejected rows are never dropped silently: every reject is written,
      with its reasons, to a per-table reject CSV under
      ``data/processed/``, and a bounded sample of structured issues is
      kept on the dataset result for reporting.
"""

from __future__ import annotations

import csv
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

from sqlalchemy import Table, delete, func, select
from sqlalchemy.orm import Session, sessionmaker

from app.db.database import Base, SessionLocal
from app.importer.batch_processor import DEFAULT_BATCH_SIZE, BatchProcessor
from app.importer.csv_reader import CsvReadError, count_data_rows, read_csv, read_header
from app.importer.progress_tracker import ProgressTracker, format_duration
from app.importer.transformer import RowTransformError, RowTransformer
from app.importer.validator import RowValidator, ValidationIssue, validate_header
from app.models import (
    Bank,
    Customer,
    Error,
    InitiationMode,
    MandateOperation,
    Mcc,
    Merchant,
    Psp,
    Purpose,
    RecurrencePattern,
    Response,
    Transaction,
)

logger = logging.getLogger(__name__)

# Frozen dataset locations, resolved from this file so the pipeline works
# regardless of the caller's working directory.
PROJECT_ROOT = Path(__file__).resolve().parents[3]
MASTER_DATA_DIR = PROJECT_ROOT / "scripts" / "dataset_generator" / "master"
TRANSACTIONS_CSV = PROJECT_ROOT / "data" / "transactions.csv"
REJECT_DIR = PROJECT_ROOT / "data" / "processed"

#: Maximum structured issues kept in memory per dataset; the reject CSV
#: always receives every rejected row regardless of this bound.
MAX_TRACKED_ISSUES = 25

#: Maximum batch-error messages surfaced in a dataset's notes; the rest
#: are summarized as a count (all of them are logged when they occur).
MAX_REPORTED_BATCH_ERRORS = 5

_RULE = "=" * 62
_LINE = "-" * 62


@dataclass(frozen=True)
class DatasetSpec:
    """One CSV-to-table import definition.

    Attributes:
        label: Human label used in logs, progress, and the summary.
        model: ORM model class mapped to the target table.
        csv_path: Source CSV location.
        batch_size: Optional per-dataset batch size override.
    """

    label: str
    model: type[Base]
    csv_path: Path
    batch_size: int | None = None


def build_dataset_specs() -> list[DatasetSpec]:
    """Build the ordered list of every dataset the platform imports.

    Purpose:
        Single source of truth for the frozen import order — masters in
        their mandated sequence, the transaction fact strictly last.

    Returns:
        The twelve :class:`DatasetSpec` entries in import order.
    """

    return [
        DatasetSpec("Banks", Bank, MASTER_DATA_DIR / "bank_master.csv"),
        DatasetSpec("PSPs", Psp, MASTER_DATA_DIR / "psp_master.csv"),
        DatasetSpec("MCCs", Mcc, MASTER_DATA_DIR / "mcc_master.csv"),
        DatasetSpec("Purposes", Purpose, MASTER_DATA_DIR / "purpose_master.csv"),
        DatasetSpec("Responses", Response, MASTER_DATA_DIR / "response_master.csv"),
        DatasetSpec("Errors", Error, MASTER_DATA_DIR / "error_master.csv"),
        DatasetSpec(
            "Initiation Modes", InitiationMode,
            MASTER_DATA_DIR / "initiation_mode_master.csv",
        ),
        DatasetSpec(
            "Mandate Operations", MandateOperation,
            MASTER_DATA_DIR / "mandate_operation_master.csv",
        ),
        DatasetSpec(
            "Recurrence Patterns", RecurrencePattern,
            MASTER_DATA_DIR / "recurrence_pattern_master.csv",
        ),
        DatasetSpec("Customers", Customer, MASTER_DATA_DIR / "customer_master.csv"),
        DatasetSpec("Merchants", Merchant, MASTER_DATA_DIR / "merchant_master.csv"),
        DatasetSpec("Transactions", Transaction, TRANSACTIONS_CSV, batch_size=10_000),
    ]


@dataclass
class DatasetResult:
    """Statistics and outcome of one dataset import.

    Attributes:
        label: Dataset label from the spec.
        table: Target database table name.
        csv_path: Source file.
        status: IMPORTED / PARTIAL / SKIPPED / FAILED / BLOCKED.
        csv_rows: Data rows found in the CSV (progress estimate).
        inserted: Rows committed to the database.
        rejected: Rows rejected by validation/transformation.
        failed_rows: Rows lost to rolled-back batches.
        failed_batches: Batches rolled back.
        duration_seconds: Wall-clock duration of the dataset import.
        issues: Bounded sample of structured validation issues.
        notes: Human-readable remarks (skip reasons, batch errors, ...).
    """

    label: str
    table: str
    csv_path: str
    status: str = "PENDING"
    csv_rows: int = 0
    inserted: int = 0
    rejected: int = 0
    failed_rows: int = 0
    failed_batches: int = 0
    duration_seconds: float = 0.0
    issues: list[ValidationIssue] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


@dataclass
class ImportSummary:
    """Aggregated outcome of a full import run.

    Attributes:
        results: Per-dataset results in import order.
        total_duration_seconds: Wall-clock duration of the whole run.
    """

    results: list[DatasetResult]
    total_duration_seconds: float = 0.0


class _RejectWriter:
    """Lazily-opened CSV sink for rejected rows of one table.

    The file is only created when the first reject occurs, so clean imports
    leave no empty artifacts behind.
    """

    def __init__(self, directory: Path, table_name: str, header: list[str]) -> None:
        self._path = directory / f"rejects_{table_name}.csv"
        self._header = header
        self._handle: Any | None = None
        self._writer: Any | None = None

    def write(self, row: dict[str, str | None], issues: list[ValidationIssue]) -> None:
        if self._writer is None:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._handle = self._path.open("w", newline="", encoding="utf-8")
            self._writer = csv.writer(self._handle)
            self._writer.writerow(self._header + ["__reject_reasons__"])
        reasons = "; ".join(f"{i.column}: {i.reason}" for i in issues)
        self._writer.writerow([row.get(name) or "" for name in self._header] + [reasons])

    def close(self) -> str | None:
        """Close the sink; returns the file path if any reject was written."""
        if self._handle is None:
            return None
        self._handle.close()
        self._handle = None
        self._writer = None
        return str(self._path)


class ImportService:
    """Orchestrator of the full, ordered enterprise CSV import.

    Purpose:
        The single entry point of Phase 5B: hand it a session factory and
        call :meth:`run_full_import`.

    Parameters:
        session_factory: Session factory bound to the target database;
            defaults to the application's ``SessionLocal``.
        batch_size: Optional global batch-size override applied to every
            dataset (takes precedence over per-dataset defaults).
        reset: When ``True``, tables that already hold rows are cleared and
            re-imported instead of being skipped.
        reject_dir: Directory receiving per-table reject CSVs.
    """

    def __init__(
        self,
        session_factory: sessionmaker[Session] = SessionLocal,
        batch_size: int | None = None,
        reset: bool = False,
        reject_dir: Path = REJECT_DIR,
    ) -> None:
        self._session_factory = session_factory
        self._batch_size = batch_size
        self._reset = reset
        self._reject_dir = reject_dir

    def run_full_import(self) -> ImportSummary:
        """Run the complete import: 11 masters in order, then transactions.

        Purpose:
            Orchestrate every dataset import, enforce the master-before-fact
            dependency, display progress, and collect run-wide statistics.

        Returns:
            An :class:`ImportSummary` with one :class:`DatasetResult` per
            dataset; render it with :func:`format_summary`.
        """

        started = time.monotonic()
        specs = build_dataset_specs()
        logger.info("Starting full enterprise import (%d datasets) ...", len(specs))

        results: list[DatasetResult] = []
        masters_failed = False
        for spec in specs:
            is_fact = spec.model is Transaction
            if is_fact and masters_failed:
                result = DatasetResult(
                    label=spec.label,
                    table=spec.model.__table__.name,
                    csv_path=str(spec.csv_path),
                    status="BLOCKED",
                    notes=[
                        "blocked: a master import failed - transactions must "
                        "never load without master data"
                    ],
                )
                logger.error("%s import BLOCKED: a master import failed.", spec.label)
            else:
                result = self._import_dataset(spec)
                if not is_fact and result.status == "FAILED":
                    masters_failed = True
            results.append(result)

        summary = ImportSummary(results, time.monotonic() - started)
        logger.info(
            "Full import finished in %s.", format_duration(summary.total_duration_seconds)
        )
        return summary

    # ------------------------------------------------------------------
    # Internal orchestration
    # ------------------------------------------------------------------
    def _import_dataset(self, spec: DatasetSpec) -> DatasetResult:
        """Run the reader → validator → transformer → batch pipeline once."""

        table: Table = spec.model.__table__
        result = DatasetResult(label=spec.label, table=table.name, csv_path=str(spec.csv_path))
        started = time.monotonic()
        logger.info("Starting %s import from %s ...", spec.label, spec.csv_path.name)

        try:
            header = read_header(spec.csv_path)
        except CsvReadError as exc:
            return self._fail(result, str(exc), started)

        header_issues = validate_header(header, table)
        if header_issues:
            result.issues.extend(header_issues)
            return self._fail(
                result,
                f"header mismatch: {'; '.join(issue.reason for issue in header_issues)}",
                started,
            )

        existing = self._existing_row_count(table)
        if existing and not self._reset:
            result.status = "SKIPPED"
            result.notes.append(
                f"table already holds {existing:,} rows - rerun with --reset to reload"
            )
            result.duration_seconds = time.monotonic() - started
            logger.info("%s import skipped (%s rows already present).", spec.label, f"{existing:,}")
            return result
        if existing and self._reset:
            self._delete_existing(table)
            result.notes.append(f"reset: removed {existing:,} existing rows")
            logger.info("Reset: removed %s existing rows from '%s'.", f"{existing:,}", table.name)

        logger.info("Reading CSV and counting rows ...")
        result.csv_rows = count_data_rows(spec.csv_path)

        logger.info("Validating, transforming, and writing batches ...")
        validator = RowValidator(table)
        transformer = RowTransformer(table)
        tracker = ProgressTracker(spec.label, total=result.csv_rows)
        rejects = _RejectWriter(self._reject_dir, table.name, header)

        def pipeline() -> Iterator[dict[str, Any]]:
            """Stream rows through validation and transformation."""
            for row_number, row in enumerate(read_csv(spec.csv_path), start=1):
                issues = validator.validate_row(row, row_number)
                if issues:
                    self._reject_row(result, rejects, row, issues)
                    continue
                try:
                    yield transformer.transform(row)
                except RowTransformError as exc:
                    issue = ValidationIssue(row_number, exc.column, exc.value, exc.reason)
                    self._reject_row(result, rejects, row, [issue])

        processor = BatchProcessor(
            self._session_factory,
            batch_size=self._batch_size or spec.batch_size or DEFAULT_BATCH_SIZE,
            on_progress=lambda done: tracker.update(done + result.rejected),
        )
        stats = processor.process(table, pipeline())

        reject_path = rejects.close()
        tracker.finish(stats.inserted + stats.failed_rows + result.rejected)

        result.inserted = stats.inserted
        result.failed_rows = stats.failed_rows
        result.failed_batches = stats.failed_batches
        result.notes.extend(stats.batch_errors[:MAX_REPORTED_BATCH_ERRORS])
        if len(stats.batch_errors) > MAX_REPORTED_BATCH_ERRORS:
            result.notes.append(
                f"... and {len(stats.batch_errors) - MAX_REPORTED_BATCH_ERRORS} "
                "more batch errors"
            )
        if reject_path is not None:
            result.notes.append(f"rejected rows written to {reject_path}")

        if result.inserted == 0 and result.csv_rows > 0:
            result.status = "FAILED"
        elif result.failed_batches or result.rejected:
            result.status = "PARTIAL"
        else:
            result.status = "IMPORTED"
        result.duration_seconds = time.monotonic() - started

        logger.info(
            "%s import completed: %s inserted, %s rejected, %s lost to failed batches (%s).",
            spec.label,
            f"{result.inserted:,}",
            f"{result.rejected:,}",
            f"{result.failed_rows:,}",
            format_duration(result.duration_seconds),
        )
        return result

    @staticmethod
    def _reject_row(
        result: DatasetResult,
        rejects: _RejectWriter,
        row: dict[str, str | None],
        issues: list[ValidationIssue],
    ) -> None:
        """Record one rejected row: reject CSV, bounded sample, counter."""

        rejects.write(row, issues)
        remaining = MAX_TRACKED_ISSUES - len(result.issues)
        if remaining > 0:
            result.issues.extend(issues[:remaining])
        result.rejected += 1

    def _fail(self, result: DatasetResult, reason: str, started: float) -> DatasetResult:
        """Mark a dataset as failed before any row was processed."""

        result.status = "FAILED"
        result.notes.append(reason)
        result.duration_seconds = time.monotonic() - started
        logger.error("%s import failed: %s", result.label, reason)
        return result

    def _existing_row_count(self, table: Table) -> int:
        """Return the current row count of ``table``."""

        with self._session_factory() as session:
            return session.execute(
                select(func.count()).select_from(table)
            ).scalar_one()

    def _delete_existing(self, table: Table) -> None:
        """Delete all existing rows of ``table`` (reset mode)."""

        with self._session_factory() as session:
            session.execute(delete(table))
            session.commit()


def format_summary(summary: ImportSummary) -> str:
    """Render the final import summary as plain text.

    Purpose:
        One authoritative, console/log-friendly report of the whole run:
        per-dataset rows, totals, elapsed time, throughput, validation
        errors, failed records, and success rate.

    Parameters:
        summary: The :class:`ImportSummary` returned by
            :meth:`ImportService.run_full_import`.

    Returns:
        The formatted multi-line report.
    """

    lines = [_RULE, "IMPORT COMPLETED".center(62), _RULE]

    for result in summary.results:
        suffix = "" if result.status in ("IMPORTED", "PARTIAL") else f"  ({result.status})"
        lines.append(f"{result.label + ' Imported':<38s}{result.inserted:>18,}{suffix}")

    attempted = [r for r in summary.results if r.status not in ("SKIPPED", "BLOCKED")]
    total_inserted = sum(r.inserted for r in summary.results)
    total_rows = sum(r.csv_rows for r in attempted)
    total_rejected = sum(r.rejected for r in summary.results)
    total_failed_rows = sum(r.failed_rows for r in summary.results)
    duration = summary.total_duration_seconds
    rows_per_second = total_inserted / duration if duration > 0 else 0.0
    success_rate = (total_inserted / total_rows * 100) if total_rows else 100.0

    lines += [
        _LINE,
        f"{'Total Rows Imported':<38s}{total_inserted:>18,}",
        f"{'Elapsed Time':<38s}{format_duration(duration):>18s}",
        f"{'Rows Per Second':<38s}{rows_per_second:>18,.0f}",
        f"{'Validation Errors (rejected rows)':<38s}{total_rejected:>18,}",
        f"{'Failed Records (rolled-back rows)':<38s}{total_failed_rows:>18,}",
        f"{'Success Rate':<38s}{success_rate:>17.2f}%",
        _RULE,
    ]

    notes = [(r.label, note) for r in summary.results for note in r.notes]
    if notes:
        lines.append("Notes:")
        lines.extend(f"  - {label}: {note}" for label, note in notes)
        lines.append(_RULE)

    return "\n".join(lines)
