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


class ProfitLossLine(BaseModel):
    key: str
    label: str
    value: float
    currency: str
    section: str  # income | expense | tax
    group: str  # category key or rollup
    source: str  # ytd_actual | schedule | run_rate | assumption
    href: str | None = None


class ProfitLossTotals(BaseModel):
    ytd_income: float
    ytd_expenses: float
    ytd_net: float
    projected_income: float
    projected_expenses: float
    projected_net: float
    projected_tax: float
    projected_net_after_tax: float


class ProfitLossResponse(BaseModel):
    year: int
    ytd_start: str
    ytd_end: str
    currency: str
    days_elapsed: int
    days_in_year: int
    projection_method: str  # schedules | run_rate
    totals: ProfitLossTotals
    ytd_lines: list[ProfitLossLine]
    projection_lines: list[ProfitLossLine]
    assumptions: list[BalanceSheetAssumption]
    gaps: list[str] = []


class ForecastYear(BaseModel):
    year_index: int  # 1..horizon
    calendar_year: int
    income: float
    expenses: float
    premium: float
    loan_interest: float
    net_cashflow: float
    cash: float
    investments: float
    insurance_sv: float
    loans: float
    net_worth: float
    notes: list[str] = []


class ForecastOpening(BaseModel):
    cash: float
    investments: float
    insurance_sv: float
    loans: float
    net_worth: float
    base_income: float
    base_expenses: float
    premium_annual: float
    loan_principal: float
    loan_rate_pct: float


class ForecastResponse(BaseModel):
    currency: str
    start_year: int
    horizon_years: int
    opening: ForecastOpening
    years: list[ForecastYear]
    assumptions: list[BalanceSheetAssumption]
    gaps: list[str] = []
