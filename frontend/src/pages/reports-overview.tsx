import { useEffect, useMemo, useState, type ElementType } from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useQuery } from '@tanstack/react-query'
import {
  ChevronDown,
  ChevronRight,
  ExternalLink,
  LineChart,
  Scale,
  CalendarRange,
  BarChart3,
  Settings2,
} from 'lucide-react'
import { reports } from '@/lib/api'
import { localDateString } from '@/lib/date-utils'
import { formatCurrency } from '@/lib/format'
import { PageHeader } from '@/components/page-header'
import { DatePickerInput } from '@/components/ui/date-picker-input'
import { Skeleton } from '@/components/ui/skeleton'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { BalanceSheetT, isInsuranceLine } from '@/components/reports/balance-sheet-t'
import {
  TimeSpineTable,
  SpineTh,
  SpineTd,
  SpineLegend,
} from '@/components/reports/time-spine-table'
import { useAuth } from '@/contexts/auth-context'
import { useCollectionFilter } from '@/contexts/collection-filter-context'
import { useDisplayLocale } from '@/hooks/use-display-locale'
import { usePrivacyMode } from '@/hooks/use-privacy-mode'
import type {
  BalanceSheetAssumption,
  BalanceSheetResponse,
  ForecastResponse,
  ProfitLossLine,
  ProfitLossResponse,
  ReportResponse,
} from '@/types'
import { cn } from '@/lib/utils'

const BS_PREFS_KEY = 'securo.balanceSheet.prefs'
const PL_PREFS_KEY = 'securo.profitLoss.prefs'
const FC_PREFS_KEY = 'securo.forecast.prefs'
const OV_PREFS_KEY = 'securo.reportsOverview.prefs'

type InsuranceBasis = 'recorded' | 'sad' | 'sv'

type OverviewPrefs = {
  insurance_value_basis: InsuranceBasis
  income_growth_pct: number
  expense_growth_pct: number
  include_tax: boolean
  effective_tax_rate: number
  horizon_years: number
  inflation_pct: number
  loan_rate_pct: number | null
  rate_reset: 'none' | 'use_assumption'
  sv_path: 'illus_table' | 'hold_flat' | 'live'
  premium_annual: number | null
}

function loadJson<T>(key: string): Partial<T> {
  try {
    const raw = localStorage.getItem(key)
    if (!raw) return {}
    return JSON.parse(raw) as Partial<T>
  } catch {
    return {}
  }
}

function loadOverviewPrefs(): OverviewPrefs {
  const bs = loadJson<{ insurance_value_basis: InsuranceBasis }>(BS_PREFS_KEY)
  const pl = loadJson<{
    income_growth_pct: number
    expense_growth_pct: number
    include_tax: boolean
    effective_tax_rate: number
  }>(PL_PREFS_KEY)
  const fc = loadJson<{
    horizon_years: number
    inflation_pct: number
    income_growth_pct: number
    expense_growth_pct: number
    loan_rate_pct: number | null
    rate_reset: 'none' | 'use_assumption'
    sv_path: 'illus_table' | 'hold_flat' | 'live'
    premium_annual: number | null
  }>(FC_PREFS_KEY)
  const ov = loadJson<OverviewPrefs>(OV_PREFS_KEY)
  const basis = ov.insurance_value_basis ?? bs.insurance_value_basis ?? 'recorded'
  return {
    insurance_value_basis:
      basis === 'sad' || basis === 'sv' || basis === 'recorded' ? basis : 'recorded',
    income_growth_pct: Number(ov.income_growth_pct ?? pl.income_growth_pct ?? fc.income_growth_pct ?? 0) || 0,
    expense_growth_pct: Number(ov.expense_growth_pct ?? pl.expense_growth_pct ?? fc.expense_growth_pct ?? 0) || 0,
    include_tax: Boolean(ov.include_tax ?? pl.include_tax ?? false),
    effective_tax_rate: Number(ov.effective_tax_rate ?? pl.effective_tax_rate ?? 0) || 0,
    horizon_years: Number(ov.horizon_years ?? fc.horizon_years ?? 5) || 5,
    inflation_pct: Number(ov.inflation_pct ?? fc.inflation_pct ?? 0) || 0,
    loan_rate_pct:
      ov.loan_rate_pct !== undefined
        ? ov.loan_rate_pct
        : fc.loan_rate_pct !== undefined
          ? fc.loan_rate_pct
          : null,
    rate_reset: (ov.rate_reset ?? fc.rate_reset ?? 'none') as OverviewPrefs['rate_reset'],
    sv_path: (ov.sv_path ?? fc.sv_path ?? 'illus_table') as OverviewPrefs['sv_path'],
    premium_annual:
      ov.premium_annual !== undefined
        ? ov.premium_annual
        : fc.premium_annual !== undefined
          ? fc.premium_annual
          : null,
  }
}

function persistPrefs(prefs: OverviewPrefs) {
  localStorage.setItem(OV_PREFS_KEY, JSON.stringify(prefs))
  localStorage.setItem(
    BS_PREFS_KEY,
    JSON.stringify({ insurance_value_basis: prefs.insurance_value_basis }),
  )
  localStorage.setItem(
    PL_PREFS_KEY,
    JSON.stringify({
      income_growth_pct: prefs.income_growth_pct,
      expense_growth_pct: prefs.expense_growth_pct,
      include_tax: prefs.include_tax,
      effective_tax_rate: prefs.effective_tax_rate,
    }),
  )
  localStorage.setItem(
    FC_PREFS_KEY,
    JSON.stringify({
      horizon_years: prefs.horizon_years,
      inflation_pct: prefs.inflation_pct,
      income_growth_pct: prefs.income_growth_pct,
      expense_growth_pct: prefs.expense_growth_pct,
      loan_rate_pct: prefs.loan_rate_pct,
      rate_reset: prefs.rate_reset,
      sv_path: prefs.sv_path,
      premium_annual: prefs.premium_annual,
    }),
  )
}

function classifyExpense(label: string): 'premiums' | 'interest' | 'living' {
  const l = label.toLowerCase()
  if (/premium|insurance|pru|policy|lic|hdfc life/.test(l)) return 'premiums'
  if (/interest|emi|loan|debt/.test(l)) return 'interest'
  return 'living'
}

function shortSvPath(v: OverviewPrefs['sv_path']): string {
  if (v === 'illus_table') return 'illus'
  if (v === 'hold_flat') return 'flat'
  return 'live'
}

function shortRateReset(v: OverviewPrefs['rate_reset']): string {
  return v === 'use_assumption' ? 'assume' : 'none'
}

function monthLabel(dateStr: string, locale: string): string {
  // Accept YYYY-MM or YYYY-MM-DD or already-formatted labels
  const m = dateStr.match(/^(\d{4})-(\d{2})/)
  if (!m) return dateStr
  const d = new Date(Number(m[1]), Number(m[2]) - 1, 1)
  return d.toLocaleString(locale, { month: 'short' })
}

function sumByClass(lines: ProfitLossLine[], cls: 'premiums' | 'interest' | 'living') {
  return lines
    .filter((l) => l.section === 'expense' || l.section === 'tax')
    .filter((l) => classifyExpense(l.label) === cls)
    .reduce((s, l) => s + l.value, 0)
}

function SectionHead({
  title,
  href,
  linkLabel,
  icon: Icon,
}: {
  title: string
  href: string
  linkLabel: string
  icon: ElementType
}) {
  return (
    <div className="flex items-center justify-between gap-3 mb-2">
      <div className="flex items-center gap-2 min-w-0">
        <div className="size-6 rounded-md bg-muted flex items-center justify-center shrink-0">
          <Icon className="size-3.5 text-foreground" />
        </div>
        <h2 className="text-sm font-semibold tracking-tight truncate">{title}</h2>
      </div>
      <Link
        to={href}
        className="text-[11px] font-medium text-foreground/70 hover:text-foreground inline-flex items-center gap-1 shrink-0"
      >
        {linkLabel}
        <ExternalLink className="size-3" />
      </Link>
    </div>
  )
}

function KpiCard({
  label,
  value,
  tone,
  hint,
  emphasize,
}: {
  label: string
  value: string
  tone?: 'good' | 'bad' | 'neutral'
  hint?: string
  emphasize?: boolean
}) {
  return (
    <div
      className={cn(
        'rounded-lg px-2.5 py-2 min-w-0',
        emphasize ? 'bg-muted/60' : 'bg-transparent',
      )}
    >
      <p className="text-[11px] text-foreground/65 truncate">{label}</p>
      <p
        className={cn(
          'text-base sm:text-lg font-semibold tabular-nums tracking-tight mt-0.5 truncate',
          tone === 'good' && 'text-emerald-700 dark:text-emerald-300',
          tone === 'bad' && 'text-rose-700 dark:text-rose-300',
        )}
      >
        {value}
      </p>
      {hint && <p className="text-[10px] text-foreground/55 mt-0.5 truncate">{hint}</p>}
    </div>
  )
}

function AssumptionChip({
  label,
  value,
  onClick,
}: {
  label: string
  value: string
  onClick?: () => void
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="inline-flex items-center gap-1 rounded-full border border-border bg-muted/50 hover:bg-muted px-2 py-0.5 text-[10px] sm:text-[11px] transition-colors"
    >
      <span className="text-foreground/65">{label}</span>
      <span className="font-medium text-foreground tabular-nums">{value}</span>
    </button>
  )
}

function toneClass(n: number, invert = false) {
  const good = invert ? n < 0 : n >= 0
  if (n === 0) return ''
  return good
    ? 'text-emerald-700 dark:text-emerald-300'
    : 'text-rose-700 dark:text-rose-300'
}

export default function ReportsOverviewPage() {
  const { t } = useTranslation()
  const { mask } = usePrivacyMode()
  const { user } = useAuth()
  const locale = useDisplayLocale()
  const userCurrency = user?.preferences?.currency_display ?? 'USD'
  const { activeAccountIds, activeWalletIds } = useCollectionFilter()
  const currentYear = new Date().getFullYear()

  const [asOf, setAsOf] = useState(localDateString())
  const [year, setYear] = useState(currentYear)
  const [prefs, setPrefs] = useState<OverviewPrefs>(() => loadOverviewPrefs())
  const [assumptionsOpen, setAssumptionsOpen] = useState(false)
  const [plIncomeOpen, setPlIncomeOpen] = useState(false)
  const [plLivingOpen, setPlLivingOpen] = useState(false)

  useEffect(() => {
    persistPrefs(prefs)
  }, [prefs])

  const accountIds = activeAccountIds ?? undefined
  const walletIds = activeWalletIds ?? undefined

  const bsQuery = useQuery<BalanceSheetResponse>({
    queryKey: ['balance-sheet', asOf, prefs.insurance_value_basis, activeAccountIds, activeWalletIds],
    queryFn: () =>
      reports.balanceSheet(asOf, prefs.insurance_value_basis, accountIds, walletIds),
  })

  const plQuery = useQuery<ProfitLossResponse>({
    queryKey: [
      'profit-loss',
      year,
      prefs.income_growth_pct,
      prefs.expense_growth_pct,
      prefs.include_tax,
      prefs.effective_tax_rate,
      activeAccountIds,
    ],
    queryFn: () =>
      reports.profitLoss({
        year,
        incomeGrowthPct: prefs.income_growth_pct,
        expenseGrowthPct: prefs.expense_growth_pct,
        includeTax: prefs.include_tax,
        effectiveTaxRate: prefs.effective_tax_rate,
        accountIds,
      }),
  })

  const fcQuery = useQuery<ForecastResponse>({
    queryKey: [
      'forecast',
      prefs.horizon_years,
      prefs.inflation_pct,
      prefs.income_growth_pct,
      prefs.expense_growth_pct,
      prefs.loan_rate_pct,
      prefs.rate_reset,
      prefs.sv_path,
      prefs.premium_annual,
      activeAccountIds,
    ],
    queryFn: () =>
      reports.forecast({
        horizonYears: prefs.horizon_years,
        inflationPct: prefs.inflation_pct,
        incomeGrowthPct: prefs.income_growth_pct,
        expenseGrowthPct: prefs.expense_growth_pct,
        loanRatePct: prefs.loan_rate_pct ?? undefined,
        rateReset: prefs.rate_reset,
        svPath: prefs.sv_path,
        premiumAnnual: prefs.premium_annual ?? undefined,
        accountIds,
      }),
  })

  // Monthly Mo spine — reuse income-expenses (no new API)
  const ieQuery = useQuery<ReportResponse>({
    queryKey: ['income-expenses-mo', year, activeAccountIds],
    queryFn: () =>
      reports.incomeExpenses(
        year === currentYear ? 12 : 24,
        'monthly',
        accountIds,
        year === currentYear ? 'ytd' : undefined,
      ),
  })

  const currency =
    bsQuery.data?.currency ?? plQuery.data?.currency ?? fcQuery.data?.currency ?? userCurrency

  const loading = bsQuery.isLoading || plQuery.isLoading || fcQuery.isLoading
  const errored = bsQuery.isError && plQuery.isError && fcQuery.isError

  const ytdIncome = useMemo(
    () => (plQuery.data?.ytd_lines ?? []).filter((l) => l.section === 'income'),
    [plQuery.data],
  )
  const ytdExpense = useMemo(
    () =>
      (plQuery.data?.ytd_lines ?? []).filter(
        (l) => l.section === 'expense' || l.section === 'tax',
      ),
    [plQuery.data],
  )
  const ytdLivingLines = useMemo(
    () => ytdExpense.filter((l) => classifyExpense(l.label) === 'living'),
    [ytdExpense],
  )

  const monthCols = useMemo(() => {
    const trend = ieQuery.data?.trend ?? []
    return trend.filter((dp) => {
      const m = dp.date.match(/^(\d{4})/)
      return m ? Number(m[1]) === year : dp.date.includes(String(year))
    })
  }, [ieQuery.data, year])

  const growthPct = Math.max(prefs.income_growth_pct, prefs.expense_growth_pct)
  const insuranceSv = useMemo(
    () =>
      (bsQuery.data?.lines ?? [])
        .filter((l) => isInsuranceLine(l))
        .reduce((s, l) => s + l.value, 0),
    [bsQuery.data],
  )
  const savingsRate = useMemo(() => {
    const income = plQuery.data?.totals.ytd_income ?? 0
    const net = plQuery.data?.totals.ytd_net ?? 0
    if (income <= 0) return null
    return (net / income) * 100
  }, [plQuery.data])
  const debtToAssets = useMemo(() => {
    const assets = bsQuery.data?.totals.assets ?? 0
    const debt = bsQuery.data?.totals.liabilities ?? 0
    if (assets <= 0) return null
    return (debt / assets) * 100
  }, [bsQuery.data])

  const ytdPremiums = useMemo(() => sumByClass(plQuery.data?.ytd_lines ?? [], 'premiums'), [plQuery.data])
  const ytdInterest = useMemo(() => sumByClass(plQuery.data?.ytd_lines ?? [], 'interest'), [plQuery.data])
  const ytdLiving = useMemo(() => sumByClass(plQuery.data?.ytd_lines ?? [], 'living'), [plQuery.data])
  const fyPremiums = useMemo(() => sumByClass(plQuery.data?.projection_lines ?? [], 'premiums'), [plQuery.data])
  const fyInterest = useMemo(() => sumByClass(plQuery.data?.projection_lines ?? [], 'interest'), [plQuery.data])
  const fyLiving = useMemo(() => sumByClass(plQuery.data?.projection_lines ?? [], 'living'), [plQuery.data])

  const assumptionChips: { key: string; label: string; value: string }[] = [
    { key: 'as_of', label: t('reportsOverview.chipAsOf'), value: asOf },
    {
      key: 'insurance_value_basis',
      label: t('reportsOverview.chipInsuranceBasis'),
      value: prefs.insurance_value_basis,
    },
    {
      key: 'include_policy_loan',
      label: t('reportsOverview.chipPolicyLoan'),
      value: 'true',
    },
    {
      key: 'growth',
      label: t('reportsOverview.chipGrowth'),
      value: `${growthPct}%`,
    },
    {
      key: 'inflation',
      label: t('reportsOverview.chipInflation'),
      value: `${prefs.inflation_pct}%`,
    },
    {
      key: 'sv_path',
      label: t('reportsOverview.chipSvPath'),
      value: shortSvPath(prefs.sv_path),
    },
    {
      key: 'rate_reset',
      label: t('reportsOverview.chipRateReset'),
      value: shortRateReset(prefs.rate_reset),
    },
  ]

  const assumptionNotes: BalanceSheetAssumption[] = useMemo(() => {
    const seen = new Set<string>()
    const out: BalanceSheetAssumption[] = []
    for (const list of [
      bsQuery.data?.assumptions ?? [],
      plQuery.data?.assumptions ?? [],
      fcQuery.data?.assumptions ?? [],
    ]) {
      for (const a of list) {
        if (seen.has(a.key)) continue
        seen.add(a.key)
        out.push(a)
      }
    }
    return out
  }, [bsQuery.data, plQuery.data, fcQuery.data])

  const fmt = (n: number) => mask(formatCurrency(n, currency, locale))
  const spineItems = [
    t('reportsOverview.spineMo'),
    t('reportsOverview.spineYtd'),
    t('reportsOverview.spineFy'),
    t('reportsOverview.spine5y'),
  ]

  const fySurplus = prefs.include_tax
    ? (plQuery.data?.totals.projected_net_after_tax ?? 0)
    : (plQuery.data?.totals.projected_net ?? 0)

  return (
    <div className="max-w-6xl mx-auto px-3 sm:px-6 pb-16">
      <PageHeader
        section={t('reportsOverview.section')}
        title={t('reportsOverview.title')}
        action={
          <div className="flex flex-wrap items-center gap-2">
            <div className="flex items-center gap-1.5">
              <Label className="text-[11px] text-foreground/65 whitespace-nowrap">
                {t('reportsOverview.asOf')}
              </Label>
              <DatePickerInput value={asOf} onChange={setAsOf} />
            </div>
            <div className="flex items-center gap-1.5">
              <Label className="text-[11px] text-foreground/65 whitespace-nowrap">
                {t('reportsOverview.year')}
              </Label>
              <Input
                type="number"
                className="w-20 h-9"
                value={year}
                min={2000}
                max={2100}
                onChange={(e) => setYear(Number(e.target.value) || currentYear)}
              />
            </div>
            <Popover open={assumptionsOpen} onOpenChange={setAssumptionsOpen}>
              <PopoverTrigger asChild>
                <Button type="button" variant="outline" size="sm" className="gap-1.5">
                  <Settings2 className="size-3.5" />
                  {t('reportsOverview.assumptions')}
                </Button>
              </PopoverTrigger>
              <PopoverContent align="end" className="w-80 max-h-[70vh] overflow-y-auto space-y-3">
                <h3 className="text-sm font-semibold">{t('reportsOverview.assumptions')}</h3>
                <div className="space-y-2">
                  <Label className="text-xs">{t('reportsOverview.chipInsuranceBasis')}</Label>
                  <Select
                    value={prefs.insurance_value_basis}
                    onValueChange={(v) =>
                      setPrefs((p) => ({ ...p, insurance_value_basis: v as InsuranceBasis }))
                    }
                  >
                    <SelectTrigger className="w-full">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="recorded">Recorded</SelectItem>
                      <SelectItem value="sad">SAD</SelectItem>
                      <SelectItem value="sv">SV</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <div className="space-y-1">
                    <Label className="text-xs">{t('reportsOverview.chipGrowth')} %</Label>
                    <Input
                      type="number"
                      value={prefs.income_growth_pct}
                      onChange={(e) =>
                        setPrefs((p) => ({
                          ...p,
                          income_growth_pct: Number(e.target.value) || 0,
                          expense_growth_pct: Number(e.target.value) || 0,
                        }))
                      }
                    />
                  </div>
                  <div className="space-y-1">
                    <Label className="text-xs">{t('reportsOverview.chipInflation')} %</Label>
                    <Input
                      type="number"
                      value={prefs.inflation_pct}
                      onChange={(e) =>
                        setPrefs((p) => ({
                          ...p,
                          inflation_pct: Number(e.target.value) || 0,
                        }))
                      }
                    />
                  </div>
                  <div className="space-y-1">
                    <Label className="text-xs">Horizon</Label>
                    <Input
                      type="number"
                      min={1}
                      max={30}
                      value={prefs.horizon_years}
                      onChange={(e) =>
                        setPrefs((p) => ({
                          ...p,
                          horizon_years: Math.min(30, Math.max(1, Number(e.target.value) || 5)),
                        }))
                      }
                    />
                  </div>
                  <div className="space-y-1 flex items-end justify-between gap-2 pb-1">
                    <Label className="text-xs">Tax</Label>
                    <Switch
                      checked={prefs.include_tax}
                      onCheckedChange={(checked) =>
                        setPrefs((p) => ({ ...p, include_tax: checked }))
                      }
                    />
                  </div>
                </div>
                {prefs.include_tax && (
                  <div className="space-y-1">
                    <Label className="text-xs">Tax %</Label>
                    <Input
                      type="number"
                      value={prefs.effective_tax_rate}
                      onChange={(e) =>
                        setPrefs((p) => ({
                          ...p,
                          effective_tax_rate: Number(e.target.value) || 0,
                        }))
                      }
                    />
                  </div>
                )}
                <div className="space-y-1">
                  <Label className="text-xs">{t('reportsOverview.chipSvPath')}</Label>
                  <Select
                    value={prefs.sv_path}
                    onValueChange={(v) =>
                      setPrefs((p) => ({
                        ...p,
                        sv_path: v as OverviewPrefs['sv_path'],
                      }))
                    }
                  >
                    <SelectTrigger className="w-full">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="illus_table">illus</SelectItem>
                      <SelectItem value="hold_flat">flat</SelectItem>
                      <SelectItem value="live">live</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                {assumptionNotes.length > 0 && (
                  <div className="rounded-lg bg-muted/50 p-2.5 space-y-1.5">
                    {assumptionNotes.map((a) => (
                      <div key={a.key} className="text-[11px]">
                        <span className="font-medium">{a.label}</span>
                        <span className="text-foreground/65"> · {a.value}</span>
                      </div>
                    ))}
                  </div>
                )}
              </PopoverContent>
            </Popover>
          </div>
        }
      />

      {/* Assumption chips — short labels only */}
      <div className="flex flex-wrap gap-1.5 mb-4 -mt-1">
        {assumptionChips.map((c) => (
          <AssumptionChip
            key={c.key}
            label={c.label}
            value={c.value}
            onClick={() => setAssumptionsOpen(true)}
          />
        ))}
        <Link
          to="/reports/charts"
          className="inline-flex items-center gap-1 rounded-full border border-dashed border-border px-2 py-0.5 text-[10px] sm:text-[11px] text-foreground/65 hover:text-foreground"
        >
          <BarChart3 className="size-3" />
          {t('reportsOverview.chartsLink')}
        </Link>
      </div>

      {loading && (
        <div className="space-y-3">
          <div className="grid grid-cols-2 md:grid-cols-5 gap-2">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-14 rounded-lg" />
            ))}
          </div>
          <Skeleton className="h-40 w-full rounded-xl" />
          <Skeleton className="h-56 w-full rounded-xl" />
        </div>
      )}

      {errored && (
        <div className="rounded-xl border border-border bg-card p-6 text-center">
          <p className="font-medium">{t('reportsOverview.loadError')}</p>
        </div>
      )}

      {!loading && !errored && (
        <>
          <div className="rounded-xl border border-border bg-card p-2.5 sm:p-3 mb-6">
            <div className="grid grid-cols-2 md:grid-cols-5 gap-2">
              <KpiCard
                label={t('reportsOverview.kpiNetWorth')}
                value={fmt(bsQuery.data?.totals.net_worth ?? 0)}
                tone={(bsQuery.data?.totals.net_worth ?? 0) >= 0 ? 'good' : 'bad'}
                emphasize
              />
              <KpiCard
                label={t('reportsOverview.kpiAsOfNetWorth')}
                value={fmt(bsQuery.data?.totals.net_worth ?? 0)}
                hint={asOf}
              />
              <KpiCard
                label={t('reportsOverview.kpiSavingsRate')}
                value={savingsRate == null ? '—' : `${savingsRate.toFixed(1)}%`}
                tone={savingsRate == null ? 'neutral' : savingsRate >= 0 ? 'good' : 'bad'}
                emphasize
              />
              <KpiCard
                label={t('reportsOverview.kpiDebtToAssets')}
                value={debtToAssets == null ? '—' : `${debtToAssets.toFixed(1)}%`}
                tone={
                  debtToAssets == null ? 'neutral' : debtToAssets > 50 ? 'bad' : 'neutral'
                }
              />
              <KpiCard
                label={t('reportsOverview.kpiInsuranceSv')}
                value={fmt(insuranceSv)}
                hint={
                  prefs.insurance_value_basis === 'sv'
                    ? t('reportsOverview.kpiInsuranceSvIllus')
                    : prefs.insurance_value_basis === 'sad'
                      ? 'SAD'
                      : t('reportsOverview.kpiInsuranceSvLive')
                }
              />
            </div>
          </div>

          {/* P&L — Mo → YTD → FY → 5Y */}
          <section className="mb-8">
            <SectionHead
              title={t('reportsOverview.plTitle')}
              href="/reports/profit-loss"
              linkLabel={t('reportsOverview.plOpen')}
              icon={LineChart}
            />
            <SpineLegend items={spineItems} />
            {plQuery.isError ? (
              <p className="text-sm text-foreground/70">{t('reportsOverview.loadError')}</p>
            ) : plQuery.data ? (
              <TimeSpineTable>
                <thead>
                  <tr>
                    <SpineTh stickyLabel align="left">
                      {year}
                    </SpineTh>
                    {monthCols.map((dp) => (
                      <SpineTh key={dp.date}>{monthLabel(dp.date, locale)}</SpineTh>
                    ))}
                    <SpineTh>{t('reportsOverview.plYtd')}</SpineTh>
                    <SpineTh>{t('reportsOverview.plFy')}</SpineTh>
                    {(fcQuery.data?.years ?? []).map((y) => (
                      <SpineTh key={`fy-${y.calendar_year}`}>{y.calendar_year}</SpineTh>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {/* Income */}
                  <tr>
                    <SpineTd stickyLabel align="left" className="font-semibold">
                      <button
                        type="button"
                        className="inline-flex items-center gap-1"
                        onClick={() => setPlIncomeOpen((v) => !v)}
                      >
                        {plIncomeOpen ? (
                          <ChevronDown className="size-3" />
                        ) : (
                          <ChevronRight className="size-3" />
                        )}
                        {t('reportsOverview.plIncome')}
                      </button>
                    </SpineTd>
                    {monthCols.map((dp) => (
                      <SpineTd key={dp.date} className={toneClass(dp.breakdowns.income ?? 0)}>
                        {fmt(dp.breakdowns.income ?? 0)}
                      </SpineTd>
                    ))}
                    <SpineTd className={cn('font-semibold', toneClass(plQuery.data.totals.ytd_income))}>
                      {fmt(plQuery.data.totals.ytd_income)}
                    </SpineTd>
                    <SpineTd className={cn('font-semibold', toneClass(plQuery.data.totals.projected_income))}>
                      {fmt(plQuery.data.totals.projected_income)}
                    </SpineTd>
                    {(fcQuery.data?.years ?? []).map((y) => (
                      <SpineTd key={`inc-${y.calendar_year}`} className={toneClass(y.income)}>
                        {fmt(y.income)}
                      </SpineTd>
                    ))}
                  </tr>
                  {plIncomeOpen &&
                    ytdIncome.map((line) => (
                      <tr key={line.key}>
                        <SpineTd stickyLabel align="left" muted className="pl-5">
                          {line.label}
                        </SpineTd>
                        {monthCols.map((dp) => (
                          <SpineTd key={dp.date} muted>
                            —
                          </SpineTd>
                        ))}
                        <SpineTd muted>{fmt(line.value)}</SpineTd>
                        <SpineTd muted>
                          {(() => {
                            const p = (plQuery.data?.projection_lines ?? []).find(
                              (x) => x.group === line.group && x.section === 'income',
                            )
                            return p ? fmt(p.value) : '—'
                          })()}
                        </SpineTd>
                        {(fcQuery.data?.years ?? []).map((y) => (
                          <SpineTd key={`inci-${y.calendar_year}`} muted>
                            —
                          </SpineTd>
                        ))}
                      </tr>
                    ))}

                  {/* Living */}
                  <tr>
                    <SpineTd stickyLabel align="left" className="font-semibold">
                      <button
                        type="button"
                        className="inline-flex items-center gap-1"
                        onClick={() => setPlLivingOpen((v) => !v)}
                      >
                        {plLivingOpen ? (
                          <ChevronDown className="size-3" />
                        ) : (
                          <ChevronRight className="size-3" />
                        )}
                        {t('reportsOverview.plLiving')}
                      </button>
                    </SpineTd>
                    {monthCols.map((dp) => (
                      <SpineTd
                        key={dp.date}
                        className={toneClass(dp.breakdowns.expenses ?? 0, true)}
                      >
                        {fmt(dp.breakdowns.expenses ?? 0)}
                      </SpineTd>
                    ))}
                    <SpineTd className={cn('font-semibold', toneClass(ytdLiving, true))}>
                      {fmt(ytdLiving)}
                    </SpineTd>
                    <SpineTd className={cn('font-semibold', toneClass(fyLiving, true))}>
                      {fmt(fyLiving)}
                    </SpineTd>
                    {(fcQuery.data?.years ?? []).map((y) => (
                      <SpineTd
                        key={`liv-${y.calendar_year}`}
                        className={toneClass(y.expenses, true)}
                      >
                        {fmt(y.expenses)}
                      </SpineTd>
                    ))}
                  </tr>
                  {plLivingOpen &&
                    ytdLivingLines.map((line) => (
                      <tr key={line.key}>
                        <SpineTd stickyLabel align="left" muted className="pl-5">
                          {line.label}
                        </SpineTd>
                        {monthCols.map((dp) => (
                          <SpineTd key={dp.date} muted>
                            —
                          </SpineTd>
                        ))}
                        <SpineTd muted>{fmt(line.value)}</SpineTd>
                        <SpineTd muted>
                          {(() => {
                            const p = (plQuery.data?.projection_lines ?? []).find(
                              (x) => x.group === line.group && x.section !== 'income',
                            )
                            return p ? fmt(p.value) : '—'
                          })()}
                        </SpineTd>
                        {(fcQuery.data?.years ?? []).map((y) => (
                          <SpineTd key={`livi-${y.calendar_year}`} muted>
                            —
                          </SpineTd>
                        ))}
                      </tr>
                    ))}

                  {/* Premiums */}
                  <tr>
                    <SpineTd stickyLabel align="left" className="font-semibold">
                      {t('reportsOverview.plPremiums')}
                    </SpineTd>
                    {monthCols.map((dp) => (
                      <SpineTd key={dp.date} muted>
                        —
                      </SpineTd>
                    ))}
                    <SpineTd className={toneClass(ytdPremiums, true)}>{fmt(ytdPremiums)}</SpineTd>
                    <SpineTd className={toneClass(fyPremiums, true)}>{fmt(fyPremiums)}</SpineTd>
                    {(fcQuery.data?.years ?? []).map((y) => (
                      <SpineTd
                        key={`prem-${y.calendar_year}`}
                        className={toneClass(y.premium, true)}
                      >
                        {fmt(y.premium)}
                      </SpineTd>
                    ))}
                  </tr>

                  {/* Interest */}
                  <tr>
                    <SpineTd stickyLabel align="left" className="font-semibold">
                      {t('reportsOverview.plInterest')}
                    </SpineTd>
                    {monthCols.map((dp) => (
                      <SpineTd key={dp.date} muted>
                        —
                      </SpineTd>
                    ))}
                    <SpineTd className={toneClass(ytdInterest, true)}>{fmt(ytdInterest)}</SpineTd>
                    <SpineTd className={toneClass(fyInterest, true)}>{fmt(fyInterest)}</SpineTd>
                    {(fcQuery.data?.years ?? []).map((y) => (
                      <SpineTd
                        key={`int-${y.calendar_year}`}
                        className={toneClass(y.loan_interest, true)}
                      >
                        {fmt(y.loan_interest)}
                      </SpineTd>
                    ))}
                  </tr>

                  {/* Surplus */}
                  <tr className="bg-muted/25">
                    <SpineTd stickyLabel align="left" className="font-semibold bg-muted/25">
                      {t('reportsOverview.plCashSurplus')}
                    </SpineTd>
                    {monthCols.map((dp) => {
                      const net = (dp.breakdowns.income ?? 0) - (dp.breakdowns.expenses ?? 0)
                      return (
                        <SpineTd key={dp.date} className={cn('font-semibold', toneClass(net))}>
                          {fmt(net)}
                        </SpineTd>
                      )
                    })}
                    <SpineTd className={cn('font-semibold', toneClass(plQuery.data.totals.ytd_net))}>
                      {fmt(plQuery.data.totals.ytd_net)}
                    </SpineTd>
                    <SpineTd className={cn('font-semibold', toneClass(fySurplus))}>
                      {fmt(fySurplus)}
                    </SpineTd>
                    {(fcQuery.data?.years ?? []).map((y) => (
                      <SpineTd
                        key={`sur-${y.calendar_year}`}
                        className={cn('font-semibold', toneClass(y.net_cashflow))}
                      >
                        {fmt(y.net_cashflow)}
                      </SpineTd>
                    ))}
                  </tr>
                </tbody>
              </TimeSpineTable>
            ) : null}
          </section>

          {/* Balance sheet T — Owe | Own */}
          <section className="mb-8">
            <SectionHead
              title={t('reportsOverview.bsTitle')}
              href="/reports/balance-sheet"
              linkLabel={t('reportsOverview.bsOpen')}
              icon={Scale}
            />
            {bsQuery.isError ? (
              <p className="text-sm text-foreground/70">{t('reportsOverview.loadError')}</p>
            ) : bsQuery.data && bsQuery.data.lines.length > 0 ? (
              <BalanceSheetT
                lines={bsQuery.data.lines}
                totals={bsQuery.data.totals}
                mask={mask}
                locale={locale}
                currency={currency}
                compact
              />
            ) : bsQuery.data ? (
              <p className="text-sm text-foreground/70">{t('reportsOverview.emptyHint')}</p>
            ) : null}
          </section>

          {/* Forecast 5Y — continuous projection */}
          <section className="mb-6">
            <SectionHead
              title={t('reportsOverview.fcTitle')}
              href="/reports/forecast"
              linkLabel={t('reportsOverview.fcOpen')}
              icon={CalendarRange}
            />
            <SpineLegend items={[t('reportsOverview.spine5y')]} />
            {fcQuery.isError ? (
              <p className="text-sm text-foreground/70">{t('reportsOverview.loadError')}</p>
            ) : fcQuery.data ? (
              <TimeSpineTable>
                <thead>
                  <tr>
                    <SpineTh stickyLabel align="left">
                      {t('reportsOverview.fcYear')}
                    </SpineTh>
                    {fcQuery.data.years.map((y) => (
                      <SpineTh key={y.calendar_year}>{y.calendar_year}</SpineTh>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {(
                    [
                      ['net_worth', t('reportsOverview.fcNetWorth'), false],
                      ['cash', t('reportsOverview.fcCash'), false],
                      ['investments', t('reportsOverview.fcInvestments'), false],
                      ['insurance_sv', t('reportsOverview.fcInsurance'), false],
                      ['loans', t('reportsOverview.fcLoans'), true],
                      ['net_cashflow', t('reportsOverview.fcCashflow'), false],
                    ] as const
                  ).map(([key, label, invert]) => (
                    <tr key={key}>
                      <SpineTd stickyLabel align="left" className="font-medium">
                        {label}
                      </SpineTd>
                      {fcQuery.data!.years.map((y) => {
                        const val = y[key]
                        return (
                          <SpineTd
                            key={y.calendar_year}
                            className={cn(
                              key === 'net_worth' && 'font-semibold',
                              key === 'loans' && toneClass(val, true),
                              key === 'net_cashflow' && toneClass(val),
                              key !== 'loans' && key !== 'net_cashflow' && invert
                                ? toneClass(val, true)
                                : undefined,
                            )}
                          >
                            {fmt(val)}
                          </SpineTd>
                        )
                      })}
                    </tr>
                  ))}
                </tbody>
              </TimeSpineTable>
            ) : null}
          </section>
        </>
      )}
    </div>
  )
}
