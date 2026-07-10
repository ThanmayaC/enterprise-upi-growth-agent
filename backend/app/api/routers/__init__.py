"""API routers package — the versioned endpoint surface (Phase 9).

Aggregates every domain router into a single :data:`api_router` mounted by
the application factory under :data:`app.api.core.API_V1_PREFIX`. Each router
depends only on the Service and Analytics layers.
"""

from fastapi import APIRouter

from app.api.routers import (
    analytics,
    bank,
    customer,
    dashboard,
    health,
    merchant,
    portfolio,
    psp,
    search,
)
from app.copilot import router as copilot_router

#: The single router included by the application; order controls the tag
#: order shown in Swagger.
api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(portfolio.router)
api_router.include_router(dashboard.router)
api_router.include_router(merchant.router)
api_router.include_router(customer.router)
api_router.include_router(bank.router)
api_router.include_router(psp.router)
api_router.include_router(analytics.router)
api_router.include_router(search.router)
api_router.include_router(copilot_router)

__all__ = ["api_router"]
