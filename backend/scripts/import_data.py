"""CLI entry point for the Enterprise CSV Import Pipeline (Phase 5B).

Purpose:
    Verify the environment (database connection, schema, CSV sources), run
    the full ordered import — the 11 master tables, then the transaction
    fact — with live progress, and print the final statistics report.

Usage (from the ``backend/`` directory):

    python scripts/import_data.py [--reset] [--batch-size N] [--verbose]

Options:
    --reset        Clear tables that already hold rows and re-import them
                   (without it, populated tables are skipped — reruns are
                   idempotent by default).
    --batch-size   Override the batch size for every dataset.
    --verbose      DEBUG logging, including per-batch write logs.

Exit codes:
    0 — every dataset imported (or was deliberately skipped) cleanly.
    1 — preflight failed, or at least one dataset failed, was blocked, or
        lost rows to rejected/rolled-back batches.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

# Make ``app`` importable and anchor relative resources (the ``.env`` file is
# resolved relative to the working directory by the frozen configuration).
BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))
os.chdir(BACKEND_DIR)

from sqlalchemy import inspect  # noqa: E402

from app.db.database import engine  # noqa: E402
from app.db.health import check_database_connection  # noqa: E402
from app.importer.import_service import (  # noqa: E402
    ImportService,
    build_dataset_specs,
    format_summary,
)

logger = logging.getLogger("import_data")


def _parse_args() -> argparse.Namespace:
    """Parse and return the CLI arguments.

    Purpose:
        Keep every operator-facing knob (reset, batch size, verbosity) in
        one place with self-documenting help text.

    Returns:
        The parsed ``argparse.Namespace``.
    """

    parser = argparse.ArgumentParser(
        description="Import the frozen master CSVs and the transaction fact CSV into PostgreSQL.",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="clear already-populated tables and re-import them",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=None,
        metavar="N",
        help="override the rows-per-batch size for every dataset "
             "(default: 5000; transactions: 10000)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="enable DEBUG logging, including per-batch write logs",
    )
    return parser.parse_args()


def _configure_logging(verbose: bool) -> None:
    """Configure enterprise console logging for the import run.

    Parameters:
        verbose: When ``True``, log at DEBUG (per-batch detail); otherwise
            INFO (phase-level messages only).

    Returns:
        None.
    """

    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s  %(levelname)-8s %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stdout,
    )


def _verify_database() -> bool:
    """Verify that the configured PostgreSQL database is reachable.

    Returns:
        ``True`` when a connection round-trip succeeds; ``False`` otherwise
        (the failure cause is logged).
    """

    logger.info("Verifying database connection ...")
    health = check_database_connection()
    if not health.healthy:
        logger.error(health.detail)
        return False
    logger.info("Database connection verified.")
    return True


def _verify_schema() -> bool:
    """Verify that every target table exists in the database.

    Returns:
        ``True`` when all twelve tables are present; ``False`` otherwise
        (with a hint to run the Alembic migration).
    """

    logger.info("Verifying database schema ...")
    present = set(inspect(engine).get_table_names())
    required = {spec.model.__table__.name for spec in build_dataset_specs()}
    missing = sorted(required - present)
    if missing:
        logger.error(
            "Missing tables: %s. Run 'alembic upgrade head' from the backend/ directory first.",
            ", ".join(missing),
        )
        return False
    logger.info("All %d target tables present.", len(required))
    return True


def _verify_csv_files() -> bool:
    """Verify that every source CSV exists before any import starts.

    Returns:
        ``True`` when all twelve CSVs are present; ``False`` otherwise
        (with a regeneration hint for the merged transaction fact file).
    """

    logger.info("Verifying CSV sources ...")
    ok = True
    for spec in build_dataset_specs():
        if spec.csv_path.is_file():
            continue
        ok = False
        logger.error("CSV not found for %s: %s", spec.label, spec.csv_path)
        if spec.csv_path.name == "transactions.csv":
            logger.error(
                "Generate it by running 'python scripts/merge_csv.py' from the project root."
            )
    if ok:
        logger.info("All CSV sources present.")
    return ok


def main() -> int:
    """Run preflight checks, the full import, and the final report.

    Returns:
        Process exit code (see module docstring).
    """

    args = _parse_args()
    _configure_logging(args.verbose)

    if not (_verify_database() and _verify_schema() and _verify_csv_files()):
        return 1

    service = ImportService(batch_size=args.batch_size, reset=args.reset)
    summary = service.run_full_import()

    print(format_summary(summary))

    clean = all(result.status in ("IMPORTED", "SKIPPED") for result in summary.results)
    return 0 if clean else 1


if __name__ == "__main__":
    raise SystemExit(main())
