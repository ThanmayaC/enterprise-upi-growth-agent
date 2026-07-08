"""ORM models package.

Aggregates every SQLAlchemy model so that importing ``app.models`` is
sufficient to register the full schema on ``Base.metadata`` — the single
import point used by Alembic autogeneration and by application code.

Layout:
    - ``transaction``          — the UPI transaction fact table (approved).
    - Enterprise Reference Data Layer — one module per frozen master CSV.
"""

from app.models.bank import Bank
from app.models.customer import Customer
from app.models.error import Error
from app.models.initiation_mode import InitiationMode
from app.models.mandate_operation import MandateOperation
from app.models.mcc import Mcc
from app.models.merchant import Merchant
from app.models.psp import Psp
from app.models.purpose import Purpose
from app.models.recurrence_pattern import RecurrencePattern
from app.models.response import Response
from app.models.transaction import Transaction

__all__ = [
    "Bank",
    "Customer",
    "Error",
    "InitiationMode",
    "MandateOperation",
    "Mcc",
    "Merchant",
    "Psp",
    "Purpose",
    "RecurrencePattern",
    "Response",
    "Transaction",
]
