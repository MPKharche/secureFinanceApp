from pydantic import BaseModel


class ReportBreakdown(BaseModel):
    key: str
    label: str
    value: float
    color: str


class ReportSummary(BaseModel):
    primary_value: float
    change_amount: float
    change_percent: float | None
    breakdowns: list[ReportBreakdown]


class ReportCompositionItem(BaseModel):
    key: str
    label: str
    value: float
    color: str
    group: str


class ReportDataPoint(BaseModel):
    date: str
    value: float
    breakdowns: dict[str, float]
    change: float | None = None
    composition: list[ReportCompositionItem] = []


class ReportMeta(BaseModel):
    type: str
    series_keys: list[str]
    currency: str
    interval: str
    forecast_start_date: str | None = None
    baseline_active: bool = False
    baseline_lookback_days: int | None = None


class CategoryTrendItem(BaseModel):
    key: str
    label: str
    color: str
    total: float
    group: str
    series: list[ReportDataPoint]


class ReportResponse(BaseModel):
    summary: ReportSummary
    trend: list[ReportDataPoint]
    meta: ReportMeta
    composition: list[ReportCompositionItem] = []
    category_trend: list[CategoryTrendItem] = []


class BalanceSheetLine(BaseModel):
    key: str
    label: str
    value: float
    currency: str
    group: str  # cash_accounts | investments | loans | other_liabilities
    section: str  # assets | liabilities
    fidelity: str  # as_of | approx_current | reconstructed
    fidelity_note: str | None = None
    account_type: str | None = None
    href: str | None = None
    meta: dict | None = None


class BalanceSheetAssumption(BaseModel):
    key: str
    label: str
    value: str
    description: str
    options: list[str] | None = None


class BalanceSheetTotals(BaseModel):
    assets: float
    liabilities: float
    net_worth: float
    cash_accounts: float
    investments: float
    loans: float


class BalanceSheetResponse(BaseModel):
    as_of: str
    currency: str
    totals: BalanceSheetTotals
    lines: list[BalanceSheetLine]
    assumptions: list[BalanceSheetAssumption]
    gaps: list[str] = []
