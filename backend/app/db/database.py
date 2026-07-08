"""Database engine and session management.

Prepares the SQLAlchemy ``engine``, a configured ``SessionLocal`` factory, and
the declarative ``Base`` used by future ORM models. This module only *prepares*
the wiring: no connection to PostgreSQL is opened at import time. An actual
connection is established lazily by SQLAlchemy when a session is first used,
which will only happen once the database and models are introduced later.
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()

# --- ENGINE ------------------------------------------------------------------
# The engine is the central source of connectivity to the database. It owns the
# connection pool and knows how to talk to PostgreSQL (via the psycopg2 driver
# in the URL). There is exactly ONE engine per application.
#
# Learning note: creating the engine does NOT open a connection. SQLAlchemy is
# lazy — a real TCP connection to PostgreSQL is only established the first time
# a query runs. This is why importing this module (at app startup) does not
# require the database to be up.
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,  # gracefully handle stale/dropped connections
    future=True,
)

# --- SESSION -----------------------------------------------------------------
# ``SessionLocal`` is a factory (not a session itself). Calling ``SessionLocal()``
# produces a new Session — the short-lived "workspace" for a single unit of work
# where you add/query/flush objects and then commit or roll back.
#
# Learning note: one Session per request. Sessions are NOT thread-safe and must
# not be shared across requests.
#   - autoflush=False        -> we control when pending changes are sent to the DB
#   - autocommit=False        -> nothing is persisted until an explicit commit()
#   - expire_on_commit=False -> objects stay usable (attributes readable) after commit
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
    class_=Session,
)


# --- BASE --------------------------------------------------------------------
class Base(DeclarativeBase):
    """Declarative base class for all ORM models.

    Learning note: every ORM model will inherit from ``Base``. SQLAlchemy uses a
    single shared ``metadata`` registry on this class to track all mapped tables,
    which is what tools like Alembic later read to generate migrations. It is
    defined here (once) so models and migrations share one source of truth.

    ORM models are introduced in a later phase — none exist yet.
    """


# --- DEPENDENCY INJECTION ----------------------------------------------------
def get_db() -> Generator[Session, None, None]:
    """Yield a database session and guarantee it is closed.

    Learning note: this is a FastAPI *dependency*. An endpoint declares
    ``db: Session = Depends(get_db)`` and FastAPI runs this generator to supply a
    fresh Session, then resumes it after the response to run the ``finally``
    block. The try/finally guarantees the session is always returned to the pool,
    even if the request raises. This inverts control: endpoints receive a ready
    session instead of creating and managing one themselves.
    """

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
