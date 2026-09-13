import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery } from '@tanstack/react-query'
import { CalendarRange, Settings2, TrendingUp } from 'lucide-react'
import { reports } from '@/lib/api'
import { formatCurrency } from '@/lib/format'
import {
  FrozenScrollTable,
  FrozenTd,
  FrozenTh,
} from '@/components/ui/frozen-scroll-table'
import { PageHeader } from '@/components/page-header'
import { Skeleton } from '@/components/ui/skeleton'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
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
import { useAuth } from '@/contexts/auth-context'
import { useCollectionFilter } from '@/contexts/collection-filter-context'
import { useDisplayLocale } from '@/hooks/use-display-locale'
import { usePrivacyMode } from '@/hooks/use-privacy-mode'
import type { ForecastResponse } from '@/types'

const PREFS_KEY = 'securo.forecast.prefs'

type ForecastPrefs = {
  horizon_years: number
  inflation_pct: number
  income_growth_pct: number
  expense_growth_pct: number
  loan_rate_pct: number
  rate_reset: 'none' | 'use_assumption'
  sv_path: 'illus_table' | 'hold_flat' | 'live'
  premium_annual: number | null
}

function loadPrefs(): ForecastPrefs {
  try {
    const raw = localStorage.getItem(PREFS_KEY)
    if (!raw) {
      return {
        horizon_years: 5,
        inflation_pct: 4,
        income_growth_pct: 5,
        expense_growth_pct: 3,
        loan_rate_pct: 7.96,
        rate_reset: 'use_assumption',
        sv_path: 'illus_table',
        premium_annual: null,
      }
    }
    const parsed = JSON.parse(raw) as Partial<ForecastPrefs>
    const rateReset = parsed.rate_reset === 'none' ? 'none' : 'use_assumption'
    const svPath =
      parsed.sv_path === 'hold_flat' || parsed.sv_path === 'live'
        ? parsed.sv_path
        : 'illus_table'
    return {
      horizon_years: Math.min(30, Math.max(1, Number(parsed.horizon_years) || 5)),
      inflation_pct: Number(parsed.inflation_pct) || 0,
      income_growth_pct: Number(parsed.income_growth_pct) || 0,
      expense_growth_pct: Number(parsed.expense_growth_pct) || 0,
      loan_rate_pct: Number(parsed.loan_rate_pct) || 0,
      rate_reset: rateReset,
      sv_path: svPath,
      premium_annual:
        parsed.premium_annual === null || parsed.premium_annual === undefined
          ? null
          : Number(parsed.premium_annual),
    }
  } catch {
    return {
      horizon_years: 5,
      inflation_pct: 4,
      income_growth_pct: 5,
      expense_growth_pct: 3,
      loan_rate_pct: 7.96,
      rate_reset: 'use_assumption',
      sv_path: 'illus_table',
      premium_annual: null,
    }
  }
}

function savePrefs(prefs: ForecastPrefs) {
  localStorage.setItem(PREFS_KEY, JSON.stringify(prefs))
}

export default function ForecastPage() {
  const { t } = useTranslation()
  const { mask } = usePrivacyMode()
  const { user } = useAuth()
  const locale = useDisplayLocale()
  const userCurrency = user?.preferences?.currency_display ?? 'USD'
  const { activeAccountIds } = useCollectionFilter()

  const [prefs, setPrefs] = useState<ForecastPrefs>(() => loadPrefs())
  const [assumptionsOpen, setAssumptionsOpen] = useState(false)

  useEffect(() => {
    savePrefs(prefs)
  }, [prefs])

  const { data, isLoading, isError } = useQuery<ForecastResponse>({
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
        loanRatePct: prefs.loan_rate_pct,
        rateReset: prefs.rate_reset,
        svPath: prefs.sv_path,
        premiumAnnual: prefs.premium_annual ?? undefined,
        accountIds: activeAccountIds ?? undefined,
      }),
  })

  const currency = data?.currency ?? userCurrency
  const terminal = data?.years?.[data.years.length - 1]

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 pb-16">
      <PageHeader
        section={t('forecast.section')}
        title={t('forecast.title')}
        action={
          <div className="flex flex-wrap items-center gap-2">
            <div className="flex items-center gap-2">
              <Label className="text-xs text-muted-foreground whitespace-nowrap">
                {t('forecast.horizon')}
              </Label>
              <Input
                type="number"
                className="w-20 h-9"
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
            <Popover open={assumptionsOpen} onOpenChange={setAssumptionsOpen}>
              <PopoverTrigger asChild>
                <Button type="button" variant="outline" size="sm" className="gap-1.5">
                  <Settings2 className="size-3.5" />
                  {t('forecast.assumptions')}
                </Button>
              </PopoverTrigger>
              <PopoverContent align="end" className="w-96 max-h-[80vh] overflow-y-auto space-y-3">
                <div>
                  <h3 className="text-sm font-semibold">{t('forecast.assumptionsTitle')}</h3>
                  <p className="text-xs text-muted-foreground mt-1">
                    {t('forecast.assumptionsHint')}
                  </p>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1.5">
                    <Label className="text-xs">{t('forecast.inflation')}</Label>
                    <Input
                      type="number"
                      value={prefs.inflation_pct}
                      onChange={(e) =>
                        setPrefs((p) => ({ ...p, inflation_pct: Number(e.target.value) || 0 }))
                      }
                    />
                  </div>
                  <div className="space-y-1.5">
                    <Label className="text-xs">{t('forecast.loanRate')}</Label>
                    <Input
                      type="number"
                      step="0.01"
                      value={prefs.loan_rate_pct}
                      onChange={(e) =>
                        setPrefs((p) => ({ ...p, loan_rate_pct: Number(e.target.value) || 0 }))
                      }
                    />
                  </div>
                  <div className="space-y-1.5">
                    <Label className="text-xs">{t('forecast.incomeGrowth')}</Label>
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
                  <div className="space-y-1.5">
                    <Label className="text-xs">{t('forecast.expenseGrowth')}</Label>
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
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs">{t('forecast.rateReset')}</Label>
                  <Select
                    value={prefs.rate_reset}
                    onValueChange={(v) =>
                      setPrefs((p) => ({
                        ...p,
                        rate_reset: v as ForecastPrefs['rate_reset'],
                      }))
                    }
                  >
                    <SelectTrigger className="w-full">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none">{t('forecast.rateResetNone')}</SelectItem>
                      <SelectItem value="use_assumption">
                        {t('forecast.rateResetAssumption')}
                      </SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs">{t('forecast.svPath')}</Label>
                  <Select
                    value={prefs.sv_path}
                    onValueChange={(v) =>
                      setPrefs((p) => ({ ...p, sv_path: v as ForecastPrefs['sv_path'] }))
                    }
                  >
                    <SelectTrigger className="w-full">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="illus_table">{t('forecast.svIllus')}</SelectItem>
                      <SelectItem value="hold_flat">{t('forecast.svHold')}</SelectItem>
                      <SelectItem value="live">{t('forecast.svLive')}</SelectItem>
                    </SelectContent>
                  </Select>
                  <p className="text-[11px] text-muted-foreground">{t('forecast.svPathHelp')}</p>
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs">{t('forecast.premiumAnnual')}</Label>
                  <Input
                    type="number"
                    placeholder={t('forecast.premiumAuto')}
                    value={prefs.premium_annual ?? ''}
                    onChange={(e) => {
                      const v = e.target.value
                      setPrefs((p) => ({
                        ...p,
                        premium_annual: v === '' ? null : Number(v) || 0,
                      }))
                    }}
                  />
                </div>
                <div className="rounded-lg bg-muted/50 p-3 space-y-2">
                  {(data?.assumptions ?? []).map((a) => (
                    <div key={a.key} className="text-xs">
                      <div className="font-medium text-foreground">
                        {a.label}:{' '}
                        <span className="font-normal text-muted-foreground">{a.value}</span>
                      </div>
                      <div className="text-muted-foreground mt-0.5">{a.description}</div>
                    </div>
                  ))}
                </div>
              </PopoverContent>
            </Popover>
          </div>
        }
      />

      {isLoading && (
        <div className="space-y-4">
          <Skeleton className="h-28 w-full rounded-xl" />
          <Skeleton className="h-72 w-full rounded-xl" />
        </div>
      )}

      {isError && (
        <div className="rounded-xl border border-border bg-card p-8 text-center">
          <p className="font-medium">{t('forecast.loadError')}</p>
          <p className="text-sm text-muted-foreground mt-1">{t('forecast.loadErrorHint')}</p>
        </div>
      )}

      {!isLoading && !isError && data && (
        <>
          <div className="rounded-xl border border-border bg-gradient-to-br from-card to-muted/30 p-5 sm:p-6 mb-6">
            <div className="flex items-start justify-between gap-4 flex-wrap">
              <div>
                <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                  {t('forecast.terminalNetWorth')}
                </p>
                <p className="text-3xl sm:text-4xl font-semibold tracking-tight mt-1 tabular-nums">
                  {mask(
                    formatCurrency(terminal?.net_worth ?? data.opening.net_worth, currency, locale),
                  )}
                </p>
                <p className="text-xs text-muted-foreground mt-2">
                  {t('forecast.horizonSummary', {
                    years: data.horizon_years,
                    end: terminal?.calendar_year ?? data.start_year + data.horizon_years,
                  })}
                </p>
              </div>
              <div className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm">
                <div>
                  <p className="text-xs text-muted-foreground">{t('forecast.openingNw')}</p>
                  <p className="font-semibold tabular-nums">
                    {mask(formatCurrency(data.opening.net_worth, currency, locale))}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">{t('forecast.openingSv')}</p>
                  <p className="font-semibold tabular-nums">
                    {mask(formatCurrency(data.opening.insurance_sv, currency, locale))}
                  </p>
                </div>
              </div>
            </div>
          </div>

          <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
            <CalendarRange className="size-4" />
            {t('forecast.tableTitle')}
          </h3>
          <FrozenScrollTable className="rounded-xl mb-6">
              <thead>
                <tr>
                  <FrozenTh stickyLabel className="text-xs text-muted-foreground">{t('forecast.colYear')}</FrozenTh>
                  <FrozenTh align="right" className="text-xs text-muted-foreground">{t('forecast.colIncome')}</FrozenTh>
                  <FrozenTh align="right" className="text-xs text-muted-foreground">{t('forecast.colExpenses')}</FrozenTh>
                  <FrozenTh align="right" className="text-xs text-muted-foreground">{t('forecast.colPremium')}</FrozenTh>
                  <FrozenTh align="right" className="text-xs text-muted-foreground">{t('forecast.colInterest')}</FrozenTh>
                  <FrozenTh align="right" className="text-xs text-muted-foreground">{t('forecast.colCash')}</FrozenTh>
                  <FrozenTh align="right" className="text-xs text-muted-foreground">{t('forecast.colSv')}</FrozenTh>
                  <FrozenTh align="right" className="text-xs text-muted-foreground">{t('forecast.colLoans')}</FrozenTh>
                  <FrozenTh align="right" className="text-xs text-muted-foreground">{t('forecast.colNw')}</FrozenTh>
                </tr>
              </thead>
              <tbody>
                {data.years.map((y) => (
                  <tr key={y.year_index}>
                    <FrozenTd stickyLabel className="font-medium">
                      Y{y.year_index}
                      <span className="text-muted-foreground font-normal"> · {y.calendar_year}</span>
                    </FrozenTd>
                    <FrozenTd align="right" className="text-emerald-600 dark:text-emerald-400">
                      {mask(formatCurrency(y.income, currency, locale))}
                    </FrozenTd>
                    <FrozenTd align="right" className="text-rose-600 dark:text-rose-400">
                      {mask(formatCurrency(y.expenses, currency, locale))}
                    </FrozenTd>
                    <FrozenTd align="right">
                      {mask(formatCurrency(y.premium, currency, locale))}
                    </FrozenTd>
                    <FrozenTd align="right">
                      {mask(formatCurrency(y.loan_interest, currency, locale))}
                    </FrozenTd>
                    <FrozenTd align="right">
                      {mask(formatCurrency(y.cash, currency, locale))}
                    </FrozenTd>
                    <FrozenTd align="right">
                      {mask(formatCurrency(y.insurance_sv, currency, locale))}
                    </FrozenTd>
                    <FrozenTd align="right">
                      {mask(formatCurrency(y.loans, currency, locale))}
                    </FrozenTd>
                    <FrozenTd align="right" className="font-semibold">
                      {mask(formatCurrency(y.net_worth, currency, locale))}
                    </FrozenTd>
                  </tr>
                ))}
              </tbody>
          </FrozenScrollTable>

          <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
            <TrendingUp className="size-4" />
            {t('forecast.notesTitle')}
          </h3>
          <div className="grid gap-3 md:grid-cols-2 mb-6">
            {data.years.map((y) => (
              <div key={`n-${y.year_index}`} className="rounded-lg border border-border bg-card p-3">
                <p className="text-xs font-semibold mb-1">
                  Y{y.year_index} · {y.calendar_year}
                </p>
                <ul className="text-xs text-muted-foreground space-y-1 list-disc pl-4">
                  {(y.notes.length ? y.notes : [t('forecast.noNotes')]).map((n) => (
                    <li key={n}>{n}</li>
                  ))}
                  <li>
                    {t('forecast.netCashflow')}:{' '}
                    {mask(formatCurrency(y.net_cashflow, currency, locale))}
                  </li>
                </ul>
              </div>
            ))}
          </div>

          <section className="rounded-xl border border-dashed border-border bg-card/50 p-4 sm:p-5">
            <h2 className="text-sm font-semibold mb-2">{t('forecast.gapsTitle')}</h2>
            <ul className="text-xs text-muted-foreground space-y-1.5 list-disc pl-4">
              {(data.gaps ?? []).map((g) => (
                <li key={g}>{g}</li>
              ))}
            </ul>
          </section>
        </>
      )}
    </div>
  )
}
