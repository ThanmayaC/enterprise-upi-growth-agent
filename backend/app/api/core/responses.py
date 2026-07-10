"""Enterprise error contract and shared OpenAPI response definitions.

Purpose:
    Define the single JSON error envelope every endpoint returns on
    failure, and the reusable ``responses={...}`` map that documents those
    failures in Swagger/OpenAPI. Keeping the shape in one place guarantees
    the React workspace can handle every error identically.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ErrorBody(BaseModel):
    """The body of an enterprise error response."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "type": "not_found",
                "message": "merchant 'MER999999' does not exist",
                "status_code": 404,
                "path": "/api/v1/merchants/MER999999/profile",
            }
        }
    )

    type: str = Field(description="Machine-readable error category.")
    message: str = Field(description="Human-readable explanation.")
    status_code: int = Field(description="HTTP status code.")
    path: str | None = Field(default=None, description="Request path that failed.")
    details: list[dict[str, Any]] | None = Field(
        default=None, description="Field-level validation errors, when applicable."
    )


class ErrorResponse(BaseModel):
    """The top-level error envelope: ``{\"error\": {...}}``."""

    error: ErrorBody


def error_payload(
    *,
    error_type: str,
    message: str,
    status_code: int,
    path: str | None = None,
    details: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build the serialized error envelope for a ``JSONResponse``."""

    return ErrorResponse(
        error=ErrorBody(
            type=error_type,
            message=message,
            status_code=status_code,
            path=path,
            details=details,
        )
    ).model_dump(exclude_none=True)


#: Reusable OpenAPI documentation for the failure modes every endpoint can
#: return. Attach with ``responses=ERROR_RESPONSES`` on a router.
ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    404: {"model": ErrorResponse, "description": "Resource not found"},
    409: {"model": ErrorResponse, "description": "Business-rule conflict"},
    422: {"model": ErrorResponse, "description": "Validation error"},
    500: {"model": ErrorResponse, "description": "Internal server error"},
}
