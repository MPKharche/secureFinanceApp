from app.schemas.user import UserCreate, UserRead, UserUpdate, UserPreferences
from app.schemas.category import CategoryCreate, CategoryRead, CategoryUpdate
from app.schemas.bank_connection import (
    BankConnectionRead,
    OAuthUrlRequest,
    OAuthUrlResponse,
    OAuthCallbackRequest,
)
from app.schemas.account import AccountRead
from app.schemas.transaction import (
    TransactionCreate,
    TransactionRead,
    TransactionUpdate,
    TransactionImportPreview,
    TransactionImportRequest,
)
from app.schemas.dashboard import DashboardSummary, SpendingByCategory, MonthlyTrend
from app.schemas.loan_schedule import (  # noqa: F401
    AutoLinkRequest,
    AutoLinkResponse,
    BulkUpdateDatesRequest,
    LinkTransactionRequest,
    LoanScheduleEntryRead,
    LoanScheduleEntryUpdate,
    LoanScheduleResponse,
    LoanScheduleSummary,
    MarkPaymentStatusRequest,
    PotentialMatch,
    PrepaymentCreate,
    PrepaymentOption,
    PrepaymentRead,
    PrepaymentSimulation,
    PrepaymentSimulateRequest,
    RegenerateScheduleRequest,
)

__all__ = [
    "UserCreate",
    "UserRead",
    "UserUpdate",
    "UserPreferences",
    "CategoryCreate",
    "CategoryRead",
    "CategoryUpdate",
    "BankConnectionRead",
    "OAuthUrlRequest",
    "OAuthUrlResponse",
    "OAuthCallbackRequest",
    "AccountRead",
    "TransactionCreate",
    "TransactionRead",
    "TransactionUpdate",
    "TransactionImportPreview",
    "TransactionImportRequest",
    "DashboardSummary",
    "SpendingByCategory",
    "MonthlyTrend",
]
