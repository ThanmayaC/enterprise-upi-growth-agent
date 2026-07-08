"""Alembic migration environment.

Bridges Alembic to the application's frozen database wiring:

- The connection URL is taken from the application settings
  (``app.core.config``), so migrations always target the same database as
  the application itself — one source of truth, no URL duplicated in
  ``alembic.ini``.
- ``target_metadata`` is the application's declarative ``Base.metadata``.
  Importing :mod:`app.models` registers every ORM model (the transaction
  fact table and all 11 master tables) on that metadata, which is what
  ``alembic revision --autogenerate`` diffs against the live schema.

Run all Alembic commands from the ``backend/`` directory
(``prepend_sys_path = .`` in ``alembic.ini`` makes ``app`` importable).
"""

from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# Importing the models package is what populates Base.metadata — without
# this import autogenerate would see an empty model space and emit drops.
import app.models  # noqa: F401  (imported for its metadata side effect)
from app.core.config import get_settings
from app.db.database import Base

# Alembic Config object — provides access to values in alembic.ini.
config = context.config

# Inject the application's database URL. configparser treats '%' as an
# interpolation marker, so escape it defensively (passwords may contain it).
config.set_main_option(
    "sqlalchemy.url", get_settings().DATABASE_URL.replace("%", "%%")
)

# Set up Python logging from the ini file.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# The full application schema: fact_upi_transactions + 11 master tables.
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode — emit SQL without a DBAPI."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode — connect and apply directly."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
