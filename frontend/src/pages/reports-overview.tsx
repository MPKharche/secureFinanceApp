import { useEffect, useMemo, useState } from 'react'
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
import { useAuth } from '@/contexts/auth-context'
import { useCollectionFilter } from '@/contexts/collection-filter-context'
import { useDisplayLocale } from '@/hooks/use-display-locale'
import { usePrivacyMode } from '@/hooks/use-privacy-mode'
import type {
  BalanceSheetAssumption,
  BalanceSheetResponse,
  ForecastResponse,
  ProfitLossResponse,
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

function SectionHead({
  title,
  href,
  linkLabel,
  icon: Icon,
}: {
  title: string
  href: string
  linkLabel: string
  icon: React.ElementType
}) {
  return (
    <div className="flex items-center justify-between gap-3 mb-3">
      <div className="flex items-center gap-2 min-w-0">
        <div className="size-7 rounded-md bg-muted flex items-center justify-center shrink-0">
          <Icon className="size-3.5 text-foreground" />
        </div>
        <h2 className="text-base font-semibold tracking-tight truncate">{title}</h2>
      </div>
      <Link
        to={href}
        className="text-xs font-medium text-muted-foreground hover:text-foreground inline-flex items-center gap-1 shrink-0"
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
        'rounded-lg px-3 py-2.5 min-w-0',
        emphasize ? 'bg-muted/60' : 'bg-transparent',
      )}
    >
      <p className="text-[11px] text-muted-foreground truncate">{label}</p>
      <p
        className={cn(
          'text-lg sm:text-xl font-semibold tabular-nums tracking-tight mt-0.5 truncate',
          tone === 'good' && 'text-emerald-700 dark:text-emerald-400',
          tone === 'bad' && 'text-rose-700 dark:text-rose-400',
        )}
      >
        {value}
      </p>
      {hint && <p className="text-[10px] text-muted-foreground mt-0.5 truncate">{hint}</p>}
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
      className="inline-flex items-center gap-1.5 rounded-full border border-border bg-muted/40 hover:bg-muted px-2.5 py-1 text-[11px] transition-colors"
    >
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium text-foreground tabular-nums">{value}</span>
    </button>
  )
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
  const [plIncomeOpen, setPlIncomeOpen] = useState(true)
  const [plExpenseOpen, setPlExpenseOpen] = useState(false)

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
  const projIncome = useMemo(
    () => (plQuery.data?.projection_lines ?? []).filter((l) => l.section === 'income'),
    [plQuery.data],
  )
  const projExpense = useMemo(
    () =>
      (plQuery.data?.projection_lines ?? []).filter(
        (l) => l.section === 'expense' || l.section === 'tax',
      ),
    [plQuery.data],
  )

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
      value: prefs.sv_path,
    },
    {
      key: 'rate_reset',
      label: t('reportsOverview.chipRateReset'),
      value: prefs.rate_reset,
    },
  ]

  // Merge assumption notes from APIs for the popover list
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

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 pb-16">
      <PageHeader
        section={t('reportsOverview.section')}
        title={t('reportsOverview.title')}
        action={
          <div className="flex flex-wrap items-center gap-2">
            <div className="flex items-center gap-2">
              <Label className="text-xs text-muted-foreground whitespace-nowrap">
                {t('reportsOverview.asOf')}
              </Label>
              <DatePickerInput value={asOf} onChange={setAsOf} />
            </div>
            <div className="flex items-center gap-2">
              <Label className="text-xs text-muted-foreground whitespace-nowrap">
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
                <div>
                  <h3 className="text-sm font-semibold">{t('reportsOverview.assumptions')}</h3>
                  <p className="text-xs text-muted-foreground mt-1">
                    Shared with Balance sheet, P&amp;L, and Forecast.
                  </p>
                </div>
                <div className="space-y-2">
                  <Label className="text-xs">Insurance value</Label>
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
                      <SelectItem value="sv">SV (illustrative)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <div className="space-y-1">
                    <Label className="text-xs">Income growth %</Label>
                    <Input
                      type="number"
                      value={prefs.income_growth_pct}
                      onChange={(e) =>
                        setPrefs((p) => ({
                          ...p,
                          income_growth_pct: Number(e.target.value) || 0,
                        }))
                      }
                    />
                  </div>
                  <div className="space-y-1">
                    <Label className="text-xs">Expense growth %</Label>
                    <Input
                      type="number"
                      value={prefs.expense_growth_pct}
                      onChange={(e) =>
                        setPrefs((p) => ({
                          ...p,
                          expense_growth_pct: Number(e.target.value) || 0,
                        }))
                      }
                    />
                  </div>
                  <div className="space-y-1">
                    <Label className="text-xs">Inflation %</Label>
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
                    <Label className="text-xs">Horizon (yrs)</Label>
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
                </div>
                <div className="flex items-center justify-between gap-3">
                  <Label className="text-xs">Include tax</Label>
                  <Switch
                    checked={prefs.include_tax}
                    onCheckedChange={(checked) =>
                      setPrefs((p) => ({ ...p, include_tax: checked }))
                    }
                  />
                </div>
                {prefs.include_tax && (
                  <div className="space-y-1">
                    <Label className="text-xs">Tax rate %</Label>
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
                  <Label className="text-xs">SV path</Label>
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
                      <SelectItem value="illus_table">Illustration table</SelectItem>
                      <SelectItem value="hold_flat">Hold flat</SelectItem>
                      <SelectItem value="live">Live (fallback)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                {assumptionNotes.length > 0 && (
                  <div className="rounded-lg bg-muted/50 p-3 space-y-2">
                    {assumptionNotes.map((a) => (
                      <div key={a.key} className="text-xs">
                        <div className="font-medium">
                          {a.label}:{' '}
                          <span className="font-normal text-muted-foreground">{a.value}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </PopoverContent>
            </Popover>
          </div>
        }
      />

      <p className="text-sm text-muted-foreground -mt-2 mb-4">{t('reportsOverview.subtitle')}</p>

      {/* Assumption chips */}
      <div className="flex flex-wrap gap-2 mb-5">
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
          className="inline-flex items-center gap-1.5 rounded-full border border-dashed border-border px-2.5 py-1 text-[11px] text-muted-foreground hover:text-foreground"
        >
          <BarChart3 className="size-3" />
          {t('reportsOverview.chartsLink')}
        </Link>
      </div>

      {loading && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 md:grid-cols-5 gap-2">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-16 rounded-lg" />
            ))}
          </div>
          <Skeleton className="h-48 w-full rounded-xl" />
          <Skeleton className="h-64 w-full rounded-xl" />
        </div>
      )}

      {errored && (
        <div className="rounded-xl border border-border bg-card p-8 text-center">
          <p className="font-medium">{t('reportsOverview.loadError')}</p>
          <p className="text-sm text-muted-foreground mt-1">{t('reportsOverview.loadErrorHint')}</p>
        </div>
      )}

      {!loading && !errored && (
        <>
          {/* KPI strip — glossary: Net worth · As-of net worth · Savings rate · Debt-to-assets · Insurance SV */}
          <div className="rounded-xl border border-border bg-card p-3 sm:p-4 mb-8">
            <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
              <KpiCard
                label={t('reportsOverview.kpiNetWorth')}
                value={mask(
                  formatCurrency(bsQuery.data?.totals.net_worth ?? 0, currency, locale),
                )}
                tone={(bsQuery.data?.totals.net_worth ?? 0) >= 0 ? 'good' : 'bad'}
                emphasize
              />
              <KpiCard
                label={t('reportsOverview.kpiAsOfNetWorth')}
                value={mask(
                  formatCurrency(bsQuery.data?.totals.net_worth ?? 0, currency, locale),
                )}
                hint={asOf}
              />
              <KpiCard
                label={t('reportsOverview.kpiSavingsRate')}
                value={
                  savingsRate == null
                    ? '—'
                    : `${savingsRate >= 0 ? '' : ''}${savingsRate.toFixed(1)}%`
                }
                tone={savingsRate == null ? 'neutral' : savingsRate >= 0 ? 'good' : 'bad'}
                emphasize
              />
              <KpiCard
                label={t('reportsOverview.kpiDebtToAssets')}
                value={debtToAssets == null ? '—' : `${debtToAssets.toFixed(1)}%`}
                tone={
                  debtToAssets == null
                    ? 'neutral'
                    : debtToAssets > 50
                      ? 'bad'
                      : 'neutral'
                }
              />
              <KpiCard
                label={t('reportsOverview.kpiInsuranceSv')}
                value={mask(formatCurrency(insuranceSv, currency, locale))}
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

          {/* P&L */}
          <section className="mb-10">
            <SectionHead
              title={t('reportsOverview.plTitle')}
              href="/reports/profit-loss"
              linkLabel={t('reportsOverview.plOpen')}
              icon={LineChart}
            />
            {plQuery.isError ? (
              <p className="text-sm text-muted-foreground">{t('reportsOverview.loadError')}</p>
            ) : plQuery.data ? (
              <div className="rounded-xl border border-border overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border bg-muted/30 text-xs text-muted-foreground">
                      <th className="text-left font-medium py-2 px-3">{year}</th>
                      <th className="text-right font-medium py-2 px-3 whitespace-nowrap">
                        {t('reportsOverview.plYtd')}
                      </th>
                      <th className="text-right font-medium py-2 px-3 whitespace-nowrap hidden sm:table-cell">
                        {t('reportsOverview.plFy')}
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {/* Income row with expand */}
                    <tr className="border-b border-border/60 bg-muted/20">
                      <td className="py-2 px-3">
                        <button
                          type="button"
                          className="inline-flex items-center gap-1 text-sm font-semibold"
                          onClick={() => setPlIncomeOpen((v) => !v)}
                        >
                          {plIncomeOpen ? (
                            <ChevronDown className="size-3.5" />
                          ) : (
                            <ChevronRight className="size-3.5" />
                          )}
                          {t('reportsOverview.plIncome')}
                        </button>
                      </td>
                      <td className="py-2 px-3 text-right font-semibold tabular-nums text-emerald-700 dark:text-emerald-400">
                        {mask(formatCurrency(plQuery.data.totals.ytd_income, currency, locale))}
                      </td>
                      <td className="py-2 px-3 text-right font-semibold tabular-nums text-emerald-700 dark:text-emerald-400 hidden sm:table-cell">
                        {mask(
                          formatCurrency(plQuery.data.totals.projected_income, currency, locale),
                        )}
                      </td>
                    </tr>
                    {plIncomeOpen &&
                      ytdIncome.map((line, idx) => (
                        <tr key={`yi-${line.key}`} className="border-b border-border/40">
                          <td className="py-1.5 pl-8 pr-3 text-xs text-muted-foreground">
                            {line.label}
                          </td>
                          <td className="py-1.5 px-3 text-right text-xs tabular-nums">
                            {mask(formatCurrency(line.value, currency, locale))}
                          </td>
                          <td className="py-1.5 px-3 text-right text-xs tabular-nums hidden sm:table-cell text-muted-foreground">
                            {projIncome[idx]
                              ? mask(formatCurrency(projIncome[idx].value, currency, locale))
                              : '—'}
                          </td>
                        </tr>
                      ))}

                    <tr className="border-b border-border/60 bg-muted/20">
                      <td className="py-2 px-3">
                        <button
                          type="button"
                          className="inline-flex items-center gap-1 text-sm font-semibold"
                          onClick={() => setPlExpenseOpen((v) => !v)}
                        >
                          {plExpenseOpen ? (
                            <ChevronDown className="size-3.5" />
                          ) : (
                            <ChevronRight className="size-3.5" />
                          )}
                          {t('reportsOverview.plLiving')}
                        </button>
                      </td>
                      <td className="py-2 px-3 text-right font-semibold tabular-nums text-rose-700 dark:text-rose-400">
                        {mask(formatCurrency(plQuery.data.totals.ytd_expenses, currency, locale))}
                      </td>
                      <td className="py-2 px-3 text-right font-semibold tabular-nums text-rose-700 dark:text-rose-400 hidden sm:table-cell">
                        {mask(
                          formatCurrency(plQuery.data.totals.projected_expenses, currency, locale),
                        )}
                      </td>
                    </tr>
                    {plExpenseOpen &&
                      ytdExpense.map((line, idx) => (
                        <tr key={`ye-${line.key}`} className="border-b border-border/40">
                          <td className="py-1.5 pl-8 pr-3 text-xs text-muted-foreground">
                            {line.label}
                          </td>
                          <td className="py-1.5 px-3 text-right text-xs tabular-nums">
                            {mask(formatCurrency(line.value, currency, locale))}
                          </td>
                          <td className="py-1.5 px-3 text-right text-xs tabular-nums hidden sm:table-cell text-muted-foreground">
                            {projExpense[idx]
                              ? mask(formatCurrency(projExpense[idx].value, currency, locale))
                              : '—'}
                          </td>
                        </tr>
                      ))}

                    <tr className="bg-muted/30 border-b border-border/60">
                      <td className="py-2.5 px-3 text-sm font-semibold">
                        {t('reportsOverview.plCashSurplus')}
                      </td>
                      <td
                        className={cn(
                          'py-2.5 px-3 text-right font-semibold tabular-nums',
                          plQuery.data.totals.ytd_net >= 0
                            ? 'text-emerald-700 dark:text-emerald-400'
                            : 'text-rose-700 dark:text-rose-400',
                        )}
                      >
                        {mask(formatCurrency(plQuery.data.totals.ytd_net, currency, locale))}
                      </td>
                      <td
                        className={cn(
                          'py-2.5 px-3 text-right font-semibold tabular-nums hidden sm:table-cell',
                          plQuery.data.totals.projected_net >= 0
                            ? 'text-emerald-700 dark:text-emerald-400'
                            : 'text-rose-700 dark:text-rose-400',
                        )}
                      >
                        {mask(
                          formatCurrency(plQuery.data.totals.projected_net, currency, locale),
                        )}
                      </td>
                    </tr>
                    <tr className="bg-card">
                      <td className="py-2.5 px-3 text-sm font-semibold">
                        {t('reportsOverview.plNetAfterDebt')}
                      </td>
                      <td
                        className={cn(
                          'py-2.5 px-3 text-right font-semibold tabular-nums',
                          (prefs.include_tax
                            ? plQuery.data.totals.ytd_net
                            : plQuery.data.totals.ytd_net) >= 0
                            ? 'text-emerald-700 dark:text-emerald-400'
                            : 'text-rose-700 dark:text-rose-400',
                        )}
                      >
                        {mask(formatCurrency(plQuery.data.totals.ytd_net, currency, locale))}
                      </td>
                      <td
                        className={cn(
                          'py-2.5 px-3 text-right font-semibold tabular-nums hidden sm:table-cell',
                          (prefs.include_tax
                            ? plQuery.data.totals.projected_net_after_tax
                            : plQuery.data.totals.projected_net) >= 0
                            ? 'text-emerald-700 dark:text-emerald-400'
                            : 'text-rose-700 dark:text-rose-400',
                        )}
                      >
                        {mask(
                          formatCurrency(
                            prefs.include_tax
                              ? plQuery.data.totals.projected_net_after_tax
                              : plQuery.data.totals.projected_net,
                            currency,
                            locale,
                          ),
                        )}
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            ) : null}
          </section>

          {/* Balance sheet T */}
          <section className="mb-10">
            <SectionHead
              title={t('reportsOverview.bsTitle')}
              href="/reports/balance-sheet"
              linkLabel={t('reportsOverview.bsOpen')}
              icon={Scale}
            />
            {bsQuery.isError ? (
              <p className="text-sm text-muted-foreground">{t('reportsOverview.loadError')}</p>
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
              <p className="text-sm text-muted-foreground">{t('reportsOverview.emptyHint')}</p>
            ) : null}
          </section>

          {/* Forecast */}
          <section className="mb-6">
            <SectionHead
              title={t('reportsOverview.fcTitle')}
              href="/reports/forecast"
              linkLabel={t('reportsOverview.fcOpen')}
              icon={CalendarRange}
            />
            {fcQuery.isError ? (
              <p className="text-sm text-muted-foreground">{t('reportsOverview.loadError')}</p>
            ) : fcQuery.data ? (
              <div className="rounded-xl border border-border overflow-x-auto">
                <table className="w-full text-xs sm:text-sm">
                  <thead>
                    <tr className="border-b border-border bg-muted/30 text-[11px] text-muted-foreground">
                      <th className="text-left font-medium py-2 px-3 sticky left-0 bg-muted/30">
                        {t('reportsOverview.fcYear')}
                      </th>
                      {fcQuery.data.years.map((y) => (
                        <th
                          key={y.calendar_year}
                          className="text-right font-medium py-2 px-3 whitespace-nowrap"
                        >
                          {y.calendar_year}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {(
                      [
                        ['net_worth', t('reportsOverview.fcNetWorth')],
                        ['cash', t('reportsOverview.fcCash')],
                        ['investments', t('reportsOverview.fcInvestments')],
                        ['insurance_sv', t('reportsOverview.fcInsurance')],
                        ['loans', t('reportsOverview.fcLoans')],
                        ['net_cashflow', t('reportsOverview.fcCashflow')],
                      ] as const
                    ).map(([key, label]) => (
                      <tr key={key} className="border-b border-border/50">
                        <td className="py-2 px-3 font-medium sticky left-0 bg-card whitespace-nowrap">
                          {label}
                        </td>
                        {fcQuery.data!.years.map((y) => {
                          const val = y[key]
                          return (
                            <td
                              key={y.calendar_year}
                              className={cn(
                                'py-2 px-3 text-right tabular-nums whitespace-nowrap',
                                key === 'loans' && 'text-rose-700 dark:text-rose-400',
                                key === 'net_worth' && 'font-semibold',
                                key === 'net_cashflow' &&
                                  (val >= 0
                                    ? 'text-emerald-700 dark:text-emerald-400'
                                    : 'text-rose-700 dark:text-rose-400'),
                              )}
                            >
                              {mask(formatCurrency(val, currency, locale))}
                            </td>
                          )
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : null}
          </section>
        </>
      )}
    </div>
  )
}

