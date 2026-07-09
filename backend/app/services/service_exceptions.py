"""Service-layer exception hierarchy and repository-error translation.

Purpose:
    Give every consumer of the Service Layer (Analytics, Reports, APIs,
    AI Assistant) one consistent failure vocabulary, fully decoupled from
    the persistence layer: repository exceptions never leak upward.

Hierarchy:
    ServiceError                — base of every service-layer failure
    ├── DataNotFoundError       — a required business entity does not exist
    ├── ValidationError         — a caller-supplied argument is invalid
    └── BusinessRuleError       — an operation violates a business rule

Translation:
    Decorate public service methods with :func:`translate_repository_errors`.
    Repository failures are mapped onto the service vocabulary:

        RecordNotFoundError → DataNotFoundError
        InvalidFilterError  → ValidationError
        RepositoryError     → ServiceError
"""

from __future__ import annotations

import functools
from typing import Any, Callable, TypeVar

from app.repositories import (
    InvalidFilterError,
    RecordNotFoundError,
    RepositoryError,
)

ReturnT = TypeVar("ReturnT")


class ServiceError(Exception):
    """Base failure of the service layer."""


class DataNotFoundError(ServiceError):
    """A business entity that was required to exist could not be found."""


class ValidationError(ServiceError):
    """A caller-supplied argument failed business validation."""


class BusinessRuleError(ServiceError):
    """An operation would violate an enterprise business rule."""


def translate_repository_errors(
    func: Callable[..., ReturnT],
) -> Callable[..., ReturnT]:
    """Translate repository exceptions into service exceptions.

    Purpose:
        Enforce the layer boundary in one place: any repository failure
        escaping a decorated service method is re-raised in the service
        vocabulary, with the original exception chained for diagnostics.

    Parameters:
        func: The public service method to wrap.

    Returns:
        The wrapped method with identical signature and behaviour on
        success.
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> ReturnT:
        try:
            return func(*args, **kwargs)
        except ServiceError:
            raise  # already in the service vocabulary — pass through
        except RecordNotFoundError as exc:
            raise DataNotFoundError(str(exc)) from exc
        except InvalidFilterError as exc:
            raise ValidationError(str(exc)) from exc
        except RepositoryError as exc:
            raise ServiceError(f"data access failed: {exc}") from exc

    return wrapper


def require_non_empty(value: str, name: str) -> str:
    """Validate that a business identifier is a non-blank string.

    Purpose:
        Shared guard for identifier arguments (VPAs, names, ids) so every
        service rejects blank input identically.

    Parameters:
        value: The identifier supplied by the caller.
        name: Argument name used in the error message.

    Returns:
        The stripped identifier.

    Raises:
        ValidationError: If the value is empty or whitespace-only.
    """

    stripped = value.strip()
    if not stripped:
        raise ValidationError(f"{name} must be a non-empty string")
    return stripped
