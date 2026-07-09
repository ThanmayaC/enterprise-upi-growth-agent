"""Enterprise Repository Layer (Phase 6).

Read-only, session-injected data access over the frozen schema. Every
repository subclasses :class:`~app.repositories.base_repository.BaseRepository`
(generic lookups, filtering, ordering, pagination, safe execution) and adds
only the query methods meaningful for its table. Repositories contain no
business logic; the Phase 7 Service Layer composes them.

Usage:
    repo = TransactionRepository(session)   # session owned by the caller
    txns = repo.get_transactions_by_status("FAILURE", limit=50)

Failures surface as :class:`RepositoryError` (or its subclasses
:class:`RecordNotFoundError` / :class:`InvalidFilterError`) — never silently.
"""

from app.repositories.bank_repository import BankRepository
from app.repositories.base_repository import (
    BaseRepository,
    InvalidFilterError,
    RecordNotFoundError,
    RepositoryError,
)
from app.repositories.customer_repository import CustomerRepository
from app.repositories.error_repository import ErrorRepository
from app.repositories.initiation_mode_repository import InitiationModeRepository
from app.repositories.mandate_operation_repository import MandateOperationRepository
from app.repositories.mcc_repository import MccRepository
from app.repositories.merchant_repository import MerchantRepository
from app.repositories.psp_repository import PspRepository
from app.repositories.purpose_repository import PurposeRepository
from app.repositories.recurrence_pattern_repository import RecurrencePatternRepository
from app.repositories.response_repository import ResponseRepository
from app.repositories.transaction_repository import TransactionRepository

__all__ = [
    "BaseRepository",
    "RepositoryError",
    "RecordNotFoundError",
    "InvalidFilterError",
    "BankRepository",
    "CustomerRepository",
    "ErrorRepository",
    "InitiationModeRepository",
    "MandateOperationRepository",
    "MccRepository",
    "MerchantRepository",
    "PspRepository",
    "PurposeRepository",
    "RecurrencePatternRepository",
    "ResponseRepository",
    "TransactionRepository",
]
