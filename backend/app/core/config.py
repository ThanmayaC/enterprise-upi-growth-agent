"""Application configuration.

Centralises all runtime settings using ``pydantic-settings``. Values are loaded
from environment variables (and an optional ``.env`` file) so that configuration
stays out of the codebase (12-factor). A single, cached :class:`Settings`
instance is exposed via :func:`get_settings` to keep configuration a single
source of truth across the application.
"""

from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Strongly-typed application settings.

    Attributes are populated from environment variables. Names are
    case-insensitive; see ``.env.example`` for the supported keys.
    """

    # --- Application metadata -------------------------------------------------
    APP_NAME: str = "Enterprise UPI Growth Intelligence Platform"
    APP_ENV: str = "development"
    DEBUG: bool = True

    # --- API server -----------------------------------------------------------
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    # --- CORS -----------------------------------------------------------------
    # Comma-separated list of allowed origins (e.g. "http://localhost:3000").
    CORS_ORIGINS: list[str] = ["*"]

    # --- PostgreSQL connection parts ------------------------------------------
    # Individual components of the connection. Keeping them as discrete settings
    # makes local/CI/production overrides easy (only the differing part changes)
    # and avoids duplicating secrets across a hand-written URL.
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "upi_growth"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"

    # --- AI Copilot (Phase 12) ------------------------------------------------
    # The Copilot degrades gracefully: with no key it uses a deterministic
    # formatter, so the platform never hard-depends on an external LLM.
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_TIMEOUT: float = 30.0
    COPILOT_ENABLED: bool = True

    # --- Database URL ---------------------------------------------------------
    # Full SQLAlchemy connection string consumed by ``db/database.py``. If it is
    # left blank it is assembled from the POSTGRES_* parts above (see the
    # validator). Providing it explicitly takes precedence, which is convenient
    # for managed databases that hand you a ready-made URL.
    DATABASE_URL: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @model_validator(mode="after")
    def _assemble_and_validate_database_url(self) -> "Settings":
        """Assemble ``DATABASE_URL`` from parts when blank and validate it.

        Runs at settings-load time (i.e. import/startup). Raising here makes the
        application *fail fast with a clear message* when configuration is
        invalid, instead of surfacing a cryptic driver error much later. Note
        this only validates the *shape* of the configuration — it never opens a
        database connection.
        """

        if not self.DATABASE_URL:
            self.DATABASE_URL = (
                f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
                f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
            )

        if not self.DATABASE_URL.startswith("postgresql"):
            raise ValueError(
                "DATABASE_URL must be a PostgreSQL connection string "
                "(e.g. 'postgresql+psycopg2://user:password@host:5432/dbname'). "
                f"Got: {self.DATABASE_URL!r}"
            )

        return self


@lru_cache
def get_settings() -> Settings:
    """Return a cached singleton :class:`Settings` instance.

    Caching ensures the environment is parsed only once and that every caller
    shares the same configuration object.
    """

    return Settings()
