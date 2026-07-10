"""FastAPI application entry point.

Assembles the Enterprise REST Platform (Phase 9): instantiates FastAPI using
centralised settings, registers CORS middleware and the enterprise exception
handlers, and mounts the versioned API surface (``/api/v1``) that exposes the
Repository → Service → Analytics stack. The application layer contains no
business logic — it only exposes the existing platform over HTTP.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.core import API_V1_PREFIX, API_VERSION
from app.api.core.exceptions import register_exception_handlers
from app.api.routers import api_router
from app.core.config import Settings, get_settings

#: OpenAPI tag metadata — the professional grouping shown in Swagger.
OPENAPI_TAGS = [
    {"name": "Health", "description": "Liveness, readiness, and platform enums."},
    {"name": "Portfolio", "description": "Executive KPIs, overview, and trends."},
    {"name": "Dashboard", "description": "Executive cards, quick stats, activity."},
    {"name": "Merchant Intelligence", "description": "Merchant search, profiles, analytics."},
    {"name": "Customer Intelligence", "description": "Customer search, history, analytics."},
    {"name": "Bank Intelligence", "description": "Issuer/acquirer statistics and rankings."},
    {"name": "PSP Intelligence", "description": "PSP statistics, rankings, and trends."},
    {"name": "Analytics", "description": "Time-series analytics and the analytics catalogue."},
    {"name": "Search", "description": "Unified enterprise search across entities."},
    {"name": "AI Copilot", "description": "Orchestration layer over the intelligence stack."},
]

API_DESCRIPTION = (
    "REST platform exposing the Enterprise UPI Growth Intelligence stack — "
    "portfolio, merchant, customer, bank, PSP, and time analytics — over "
    "versioned, OpenAPI-documented endpoints. Consumed by the Enterprise "
    "React Workspace."
)


def create_app() -> FastAPI:
    """Application factory.

    Building the app inside a factory keeps construction explicit and testable
    (a fresh, fully-configured instance can be created on demand).
    """

    settings: Settings = get_settings()

    app = FastAPI(
        title=settings.APP_NAME,
        version=API_VERSION,
        description=API_DESCRIPTION,
        debug=settings.DEBUG,
        openapi_tags=OPENAPI_TAGS,
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

    # Enterprise JSON error contract for every failure mode.
    register_exception_handlers(app)

    # Versioned API surface: Repository → Service → Analytics, exposed here.
    app.include_router(api_router, prefix=API_V1_PREFIX)

    @app.get("/", tags=["Health"], summary="Service root")
    def read_root() -> dict[str, str]:
        """Root endpoint reporting that the service is running."""

        return {
            "application": settings.APP_NAME,
            "status": "Running",
            "version": API_VERSION,
            "docs": "/docs",
            "api": API_V1_PREFIX,
        }

    return app


# ASGI application instance used by Uvicorn: ``uvicorn app.main:app``.
app = create_app()
