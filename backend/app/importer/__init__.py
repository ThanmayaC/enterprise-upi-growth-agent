"""Enterprise CSV Import Pipeline (Phase 5B).

Layered, streaming ingestion of the frozen master CSVs and the transaction
fact CSV into PostgreSQL through the existing SQLAlchemy layer:

    CSV → csv_reader → validator → transformer → batch_processor → PostgreSQL

Package layout (one responsibility per module):
    - ``csv_reader``       — streaming, memory-safe CSV access
    - ``validator``        — structured schema/type/key validation
    - ``transformer``      — CSV strings → ORM-compatible values
    - ``batch_processor``  — bulk INSERT with per-batch commit/rollback
    - ``progress_tracker`` — console progress (bar, %, elapsed, ETA)
    - ``import_service``   — ordered orchestration and final statistics

Entry point: :class:`app.importer.import_service.ImportService` (or the CLI
``python scripts/import_data.py`` from the ``backend/`` directory).
"""

from app.importer.import_service import ImportService

__all__ = ["ImportService"]
