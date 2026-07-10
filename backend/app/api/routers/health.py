"""Health & metadata router — liveness, readiness, and reference enums.

Consumes only the on-demand DB health helper and static platform enums; no
business layer is touched. Metadata reference *lists* (banks, PSPs) live on
their own domain routers.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter

from app.api.core import API_VERSION
from app.api.schemas.common import DatabaseHealthResponse, HealthResponse
from app.db.health import check_database_connection

router = APIRouter(prefix="/health", tags=["Health"])


def _now() -> datetime:
    return datetime.now(timezone.utc)


@router.get("", response_model=HealthResponse, summary="Liveness probe")
def health() -> HealthResponse:
    """Report that the API process is up and serving requests."""

    return HealthResponse(
        status="ok",
        service="Enterprise UPI Growth Intelligence Platform API",
        version=API_VERSION,
        timestamp=_now(),
    )


@router.get(
    "/db",
    response_model=DatabaseHealthResponse,
    summary="Database readiness probe",
)
def database_health() -> DatabaseHealthResponse:
    """Verify PostgreSQL connectivity with a lightweight ``SELECT 1``."""

    result = check_database_connection()
    return DatabaseHealthResponse(
        status="ok" if result.healthy else "unavailable",
        healthy=result.healthy,
        detail=result.detail,
        timestamp=_now(),
    )


@router.get("/enums", summary="Supported enumerations")
def enums() -> dict[str, list[str]]:
    """Expose the platform's fixed enumerations for the workspace filters.

    Static reference values (no data-layer access) that the React workspace
    uses to build type-safe filter controls.
    """

    return {
        "transaction_status": ["SUCCESS", "FAILURE"],
        "bank_side": ["issuer", "acquirer"],
        "time_grain": ["daily", "weekly", "monthly", "quarterly", "yearly", "hourly"],
        "sort_order": ["asc", "desc"],
        "merchant_ranking_metrics": [
            "total_transactions",
            "total_amount",
            "successful_transactions",
            "success_rate",
        ],
    }
