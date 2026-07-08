"""Database health check utility.

Provides a small, side-effect-free helper to verify that the configured
PostgreSQL database is reachable. This is intentionally *not* wired to any API
endpoint or application startup hook — it is a plain function that callers
(e.g. a future ops/health router, a CLI check, or a test) can invoke on demand.
"""

from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.db.database import engine


@dataclass(frozen=True)
class DatabaseHealth:
    """Outcome of a database connectivity check.

    Attributes:
        healthy: ``True`` if a connection was opened and ``SELECT 1`` succeeded.
        detail: Human-readable description of the result (or the failure cause).
    """

    healthy: bool
    detail: str


def check_database_connection() -> DatabaseHealth:
    """Attempt a connection and run ``SELECT 1``.

    Opens a short-lived connection from the engine's pool, executes a trivial
    query to confirm the round-trip works, and returns a structured result.
    Any SQLAlchemy/driver error is caught and reported as a failure rather than
    propagated, so callers can decide how to react.

    Returns:
        A :class:`DatabaseHealth` describing success or failure.
    """

    try:
        # ``engine.connect()`` opens a real connection (this is where lazy
        # connectivity actually happens); the context manager returns it to the
        # pool afterwards.
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return DatabaseHealth(healthy=True, detail="Database connection successful.")
    except SQLAlchemyError as exc:
        return DatabaseHealth(
            healthy=False,
            detail=f"Database connection failed: {exc}",
        )
