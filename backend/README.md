# Enterprise UPI Growth Intelligence Platform — Backend

Backend for the Enterprise UPI Growth Intelligence Platform: a PostgreSQL
data layer holding one year of synthetic UPI network data (1M+ transactions
plus 11 reference masters), an enterprise CSV import pipeline, and a FastAPI
application shell. Analytics, machine learning, the recommendation engine,
and the AI growth assistant are added in later phases.

The codebase follows **Clean Architecture** principles — each responsibility
lives in its own layer, dependencies point inward, and the framework (FastAPI)
and persistence (SQLAlchemy) are kept at the edges.

---

## Project Structure

```
backend/
├── alembic/                # Database migrations (managed by Alembic)
│   └── versions/           # One migration: full initial schema (12 tables)
├── alembic.ini             # Alembic configuration (URL injected from settings)
├── app/
│   ├── api/                # HTTP routers (reserved for later phases)
│   ├── core/
│   │   └── config.py       # pydantic-settings configuration (single source of truth)
│   ├── db/
│   │   ├── database.py     # SQLAlchemy engine, SessionLocal, Base, get_db
│   │   └── health.py       # On-demand database connectivity check
│   ├── importer/           # Enterprise CSV Import Pipeline (Phase 5B)
│   │   ├── csv_reader.py       # Streaming, memory-safe CSV access
│   │   ├── validator.py        # Structured schema/type/key validation
│   │   ├── transformer.py      # CSV strings → ORM-compatible values
│   │   ├── batch_processor.py  # Bulk INSERT, commit-per-batch, rollback isolation
│   │   ├── progress_tracker.py # Console progress (bar, %, elapsed, ETA)
│   │   └── import_service.py   # Ordered orchestration + final statistics
│   ├── models/             # SQLAlchemy ORM models (transaction fact + 11 masters)
│   ├── repositories/       # Data-access layer (reserved for later phases)
│   ├── schemas/            # Pydantic API contract (reserved for later phases)
│   ├── services/           # Business logic (reserved for later phases)
│   ├── utils/              # Shared helpers (reserved for later phases)
│   └── main.py             # FastAPI application factory and entry point
├── scripts/
│   └── import_data.py      # CLI: full CSV import with preflight checks
├── requirements.txt        # Pinned Python dependencies
├── .env.example            # Sample environment configuration
└── README.md
```

### Layer responsibilities

| Layer          | Responsibility                                                        |
| -------------- | --------------------------------------------------------------------- |
| `api`          | Translate HTTP requests to service calls; no business logic.          |
| `core`         | Configuration, settings, and cross-cutting concerns.                  |
| `db`           | Engine/session lifecycle, ORM base metadata, health checks.           |
| `models`       | Persistence models: `fact_upi_transactions` + 11 master tables.       |
| `importer`     | Streaming CSV → validation → transformation → batched ORM inserts.    |
| `repositories` | Isolate persistence behind interfaces (later phases).                 |
| `schemas`      | API contract (Pydantic), decoupled from ORM models (later phases).    |
| `services`     | Orchestrate repositories and enforce domain rules (later phases).     |
| `utils`        | Small, reusable helpers with no layer dependencies.                   |

---

## Technology Stack

| Package            | Version  | Purpose                              |
| ------------------ | -------- | ------------------------------------ |
| Python             | 3.11+    | Runtime (developed on 3.13)          |
| FastAPI            | 0.139.0  | Web framework / API layer            |
| Uvicorn            | 0.51.0   | ASGI server                          |
| SQLAlchemy         | 2.0.51   | ORM and database toolkit             |
| Pydantic           | 2.13.4   | Data validation                      |
| pydantic-settings  | 2.14.2   | Environment-driven configuration     |
| Alembic            | 1.18.5   | Database migrations                  |
| psycopg2-binary    | 2.9.12   | PostgreSQL driver                    |
| PostgreSQL         | any recent | Primary data store                 |

---

## Database

Twelve tables, defined by the ORM models and created via Alembic:

- **`fact_upi_transactions`** — the transaction fact (57 columns, natural PK
  `txnid`), covering financial payments and the full Autopay mandate
  lifecycle.
- **11 master tables** — `bank_master`, `psp_master`, `mcc_master`,
  `purpose_master`, `response_master`, `error_master`,
  `initiation_mode_master`, `mandate_operation_master`,
  `recurrence_pattern_master`, `customer_master`, `merchant_master`.

Connection settings come from `.env` (see `.env.example`); `DATABASE_URL` is
assembled from the `POSTGRES_*` parts unless provided explicitly.

---

## Setup

All commands are run from the `backend/` directory.

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1        # Windows PowerShell (see .venv docs for other shells)
pip install -r requirements.txt
Copy-Item .env.example .env        # then adjust values for your PostgreSQL
```

### Apply migrations

```bash
alembic upgrade head
```

This creates all 12 tables in the configured database.

---

## Import Data

The source data is generated by `scripts/dataset_generator/` at the project
root. Masters live in `scripts/dataset_generator/master/`; the transaction
fact is merged into `data/transactions.csv` by:

```bash
# from the project root
python scripts/merge_csv.py
```

Then run the import pipeline:

```bash
# from backend/
python scripts/import_data.py              # full import with progress + summary
python scripts/import_data.py --reset      # clear populated tables and reload
python scripts/import_data.py --verbose    # DEBUG logging incl. per-batch writes
```

The CLI verifies the database connection, the schema, and every CSV before
importing; masters always load before transactions; reruns skip populated
tables (idempotent). Rejected rows are written with reasons to
`data/processed/rejects_<table>.csv`.

---

## Run the API

```bash
uvicorn app.main:app --reload
```

- Root / health endpoint: <http://localhost:8000/>
- Interactive API docs (Swagger UI): <http://localhost:8000/docs>

Expected root response:

```json
{
    "application": "Enterprise UPI Growth Intelligence Platform",
    "status": "Running"
}
```

---

## Future Phases (not yet implemented)

- Repository and service layers
- Analytics engine and growth KPIs
- ML engine and recommendation engine
- Report generation
- AI growth assistant
- React frontend
