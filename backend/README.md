# Enterprise UPI Growth Intelligence Platform — Backend

Clean, modular backend foundation for the Enterprise UPI Growth Intelligence
Platform. This is the base layer only; analytics, machine learning, the
recommendation engine, and the AI growth assistant are added in later stages.

The codebase follows **Clean Architecture** principles — each responsibility
lives in its own layer, dependencies point inward, and the framework (FastAPI)
and persistence (SQLAlchemy) are kept at the edges.

---

## Project Structure

```
backend/
├── app/
│   ├── api/            # HTTP routers and endpoint definitions (edge layer)
│   ├── core/           # Configuration and cross-cutting concerns
│   │   └── config.py   # pydantic-settings configuration (single source of truth)
│   ├── db/             # Database wiring
│   │   └── database.py # SQLAlchemy engine, SessionLocal, Base, get_db
│   ├── models/         # SQLAlchemy ORM models (added later)
│   ├── repositories/   # Data-access layer / repository pattern (added later)
│   ├── schemas/        # Pydantic request/response models (added later)
│   ├── services/       # Business/application logic (added later)
│   ├── utils/          # Shared, dependency-free helpers
│   └── main.py         # FastAPI application factory and entry point
├── requirements.txt    # Python dependencies
├── .env.example        # Sample environment configuration
├── .gitignore
└── README.md
```

### Layer responsibilities

| Layer          | Responsibility                                                        |
| -------------- | --------------------------------------------------------------------- |
| `api`          | Translate HTTP requests to service calls; no business logic.          |
| `core`         | Configuration, settings, and cross-cutting concerns.                  |
| `db`           | Engine/session lifecycle and ORM base metadata.                       |
| `models`       | Persistence models (SQLAlchemy).                                      |
| `repositories` | Isolate persistence behind interfaces so services stay ORM-agnostic.  |
| `schemas`      | API contract (Pydantic) — decoupled from ORM models.                  |
| `services`     | Orchestrate repositories and enforce domain rules.                    |
| `utils`        | Small, reusable helpers with no layer dependencies.                   |

---

## Prerequisites

- Python 3.11+
- (Later stages) PostgreSQL — **not required yet**; the app runs without a
  database connection at this foundation stage.

---

## Setup

All commands are run from the `backend/` directory.

### 1. Create a virtual environment

```bash
python -m venv .venv
```

### 2. Activate it

- **Windows (PowerShell):**
  ```powershell
  .venv\Scripts\Activate.ps1
  ```
- **Windows (cmd):**
  ```cmd
  .venv\Scripts\activate.bat
  ```
- **macOS / Linux:**
  ```bash
  source .venv/bin/activate
  ```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment

Copy the sample file and adjust values as needed:

```bash
# Windows (PowerShell)
Copy-Item .env.example .env

# macOS / Linux
cp .env.example .env
```

> The `DATABASE_URL` is prepared but not yet used to connect. No PostgreSQL
> instance is required to run the app at this stage.

---

## Run the API

With the virtual environment activated:

```bash
uvicorn app.main:app --reload
```

The server starts on <http://localhost:8000>.

- Root / health endpoint: <http://localhost:8000/>
- Interactive API docs (Swagger UI): <http://localhost:8000/docs>

### Expected root response

```json
{
    "application": "Enterprise UPI Growth Intelligence Platform",
    "status": "Running"
}
```

---

## Dependencies

| Package            | Purpose                                       |
| ------------------ | --------------------------------------------- |
| FastAPI            | Web framework / API layer                     |
| Uvicorn            | ASGI server                                   |
| SQLAlchemy         | ORM and database toolkit                      |
| Pydantic           | Data validation and schemas                   |
| pydantic-settings  | Environment-driven configuration              |
| Alembic            | Database migrations (used in later stages)    |
| psycopg2-binary    | PostgreSQL driver (used in later stages)      |
| python-dotenv      | `.env` file loading                           |
