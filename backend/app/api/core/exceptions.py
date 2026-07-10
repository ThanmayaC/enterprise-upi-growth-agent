"""Exception-to-HTTP translation for the API layer.

Purpose:
    Map the platform's Service and Analytics exception vocabularies onto
    the enterprise JSON error envelope with the correct HTTP status, in one
    place. Routers therefore never write try/except: they call services and
    analytics directly and let a raised domain exception become the right
    HTTP response.

Mapping:
    DataNotFoundError / DataUnavailableError          -> 404 not_found
    ValidationError / InvalidAnalysisRequestError     -> 422 validation_error
    BusinessRuleError                                 -> 409 conflict
    ServiceError / AnalyticsError (base)              -> 500 internal_error
    RequestValidationError (FastAPI)                  -> 422 validation_error
    HTTPException (Starlette)                         -> its own status
    Exception (anything else)                         -> 500 internal_error
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.analytics import (
    AnalyticsError,
    DataUnavailableError,
    InvalidAnalysisRequestError,
)
from app.api.core.responses import error_payload
from app.services import (
    BusinessRuleError,
    DataNotFoundError,
    ServiceError,
    ValidationError,
)

logger = logging.getLogger("app.api")


def _json(status_code: int, error_type: str, message: str, request: Request, details=None):
    """Build a ``JSONResponse`` carrying the enterprise error envelope."""

    return JSONResponse(
        status_code=status_code,
        content=error_payload(
            error_type=error_type,
            message=message,
            status_code=status_code,
            path=request.url.path,
            details=details,
        ),
    )


async def _not_found(request: Request, exc: Exception) -> JSONResponse:
    return _json(404, "not_found", str(exc), request)


async def _validation(request: Request, exc: Exception) -> JSONResponse:
    return _json(422, "validation_error", str(exc), request)


async def _conflict(request: Request, exc: Exception) -> JSONResponse:
    return _json(409, "conflict", str(exc), request)


async def _service_error(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Service failure on %s: %s", request.url.path, exc)
    return _json(500, "internal_error", "A data access error occurred.", request)


async def _request_validation(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Format FastAPI's request-validation errors into the envelope."""

    details = [
        {
            "location": list(err.get("loc", [])),
            "message": err.get("msg", ""),
            "type": err.get("type", ""),
        }
        for err in exc.errors()
    ]
    return _json(
        422, "validation_error", "Request validation failed.", request, details
    )


async def _http_exception(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    return _json(exc.status_code, "http_error", str(exc.detail), request)


async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error on %s", request.url.path)
    return _json(500, "internal_error", "An unexpected error occurred.", request)


def register_exception_handlers(app: FastAPI) -> None:
    """Register every exception handler on the application.

    Starlette resolves handlers by walking the raised exception's MRO and
    picking the closest match, so registering both the specific subclasses
    and their bases yields correct, non-overlapping behaviour.
    """

    # Service vocabulary
    app.add_exception_handler(DataNotFoundError, _not_found)
    app.add_exception_handler(ValidationError, _validation)
    app.add_exception_handler(BusinessRuleError, _conflict)
    app.add_exception_handler(ServiceError, _service_error)
    # Analytics vocabulary
    app.add_exception_handler(DataUnavailableError, _not_found)
    app.add_exception_handler(InvalidAnalysisRequestError, _validation)
    app.add_exception_handler(AnalyticsError, _service_error)
    # Framework + catch-all
    app.add_exception_handler(RequestValidationError, _request_validation)
    app.add_exception_handler(StarletteHTTPException, _http_exception)
    app.add_exception_handler(Exception, _unhandled)
