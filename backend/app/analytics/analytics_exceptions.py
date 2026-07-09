"""Analytics-layer exception hierarchy and service-error translation.

Purpose:
    Give every consumer of the Analytics Engine (ML, Recommendations,
    Reports, AI Assistant) one failure vocabulary, decoupled from the
    service layer: service exceptions never leak upward.

Hierarchy:
    AnalyticsError                  — base of every analytics failure
    ├── DataUnavailableError        — required business data is missing
    └── InvalidAnalysisRequestError — analysis parameters are invalid

Translation:
    Decorate public analytics methods with
    :func:`translate_service_errors`:

        DataNotFoundError → DataUnavailableError
        ValidationError   → InvalidAnalysisRequestError
        ServiceError      → AnalyticsError
"""

from __future__ import annotations

import functools
from typing import Any, Callable, TypeVar

from app.services import DataNotFoundError, ServiceError, ValidationError

ReturnT = TypeVar("ReturnT")


class AnalyticsError(Exception):
    """Base failure of the analytics layer."""


class DataUnavailableError(AnalyticsError):
    """Business data required for the analysis could not be found."""


class InvalidAnalysisRequestError(AnalyticsError):
    """An analysis parameter is invalid or out of supported bounds."""


def translate_service_errors(
    func: Callable[..., ReturnT],
) -> Callable[..., ReturnT]:
    """Translate service exceptions into analytics exceptions.

    Purpose:
        Enforce the layer boundary in one place: any service failure
        escaping a decorated analytics method is re-raised in the
        analytics vocabulary, with the original chained for diagnostics.

    Parameters:
        func: The public analytics method to wrap.

    Returns:
        The wrapped method with identical signature and behaviour on
        success.
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> ReturnT:
        try:
            return func(*args, **kwargs)
        except AnalyticsError:
            raise  # already in the analytics vocabulary — pass through
        except DataNotFoundError as exc:
            raise DataUnavailableError(str(exc)) from exc
        except ValidationError as exc:
            raise InvalidAnalysisRequestError(str(exc)) from exc
        except ServiceError as exc:
            raise AnalyticsError(f"business data access failed: {exc}") from exc

    return wrapper
