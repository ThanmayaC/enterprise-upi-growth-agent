"""FastAPI application entry point.

Assembles the minimal application: instantiates FastAPI using centralised
settings, registers CORS middleware, and exposes a single health/root endpoint.
Business routers, models, and services are added in later stages.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import Settings, get_settings


def create_app() -> FastAPI:
    """Application factory.

    Building the app inside a factory keeps construction explicit and testable
    (a fresh, fully-configured instance can be created on demand).
    """

    settings: Settings = get_settings()

    app = FastAPI(
        title=settings.APP_NAME,
        debug=settings.DEBUG,
    )

    # Cross-Origin Resource Sharing. Allowed origins are configuration-driven so
    # they can be tightened per environment without code changes.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/", tags=["Health"])
    def read_root() -> dict[str, str]:
        """Root endpoint reporting that the service is running."""

        return {
            "application": "Enterprise UPI Growth Intelligence Platform",
            "status": "Running",
        }

    return app


# ASGI application instance used by Uvicorn: ``uvicorn app.main:app``.
app = create_app()
