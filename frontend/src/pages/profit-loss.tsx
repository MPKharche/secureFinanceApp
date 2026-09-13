import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useQuery } from '@tanstack/react-query'
import {
  ArrowDownRight,
  ArrowUpRight,
  LineChart,
  Settings2,
  TrendingUp,
} from 'lucide-react'
import { reports } from '@/lib/api'
import { formatCurrency } from '@/lib/format'
import { PageHeader } from '@/components/page-header'
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
import { useAuth } from '@/contexts/auth-context'
import { useCollectionFilter } from '@/contexts/collection-filter-context'
import { useDisplayLocale } from '@/hooks/use-display-locale'
import { usePrivacyMode } from '@/hooks/use-privacy-mode'
import type { ProfitLossLine, ProfitLossResponse } from '@/types'

const PREFS_KEY = 'securo.profitLoss.prefs'

type PlPrefs = {
  income_growth_pct: number
  expense_growth_pct: number
  include_tax: boolean
  effective_tax_rate: number
}

function loadPrefs(): PlPrefs {
  try {
    const raw = localStorage.getItem(PREFS_KEY)
    if (!raw) {
      return {
        income_growth_pct: 0,
        expense_growth_pct: 0,
        include_tax: false,
        effective_tax_rate: 0,
      }
    }
    const parsed = JSON.parse(raw) as Partial<PlPrefs>
    return {
      income_growth_pct: Number(parsed.income_growth_pct) || 0,
      expense_growth_pct: Number(parsed.expense_growth_pct) || 0,
      include_tax: Boolean(parsed.include_tax),
      effective_tax_rate: Number(parsed.effective_tax_rate) || 0,
    }
  } catch {
    return {
      income_growth_pct: 0,
      expense_growth_pct: 0,
      include_tax: false,
      effective_tax_rate: 0,
    }
  }
}

function savePrefs(prefs: PlPrefs) {
  localStorage.setItem(PREFS_KEY, JSON.stringify(prefs))
}

function LineRow({
  line,
  mask,
  locale,
  currency,
}: {
  line: ProfitLossLine
  mask: (v: string) => string
  locale: string
  currency: string
}) {
  const amount = mask(formatCurrency(line.value, currency, locale))
  const body = (
    <div className="flex items-start justify-between gap-3 py-2.5 border-b border-border/60 last:border-0">
      <div className="min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-sm font-medium text-foreground truncate">{line.label}</span>
          <span className="text-[10px] uppercase tracking-wide px-1.5 py-0.5 rounded bg-muted text-muted-foreground">
            {line.source.replace(/_/g, ' ')}
          </span>
        </div>
      </div>
      <div className="text-sm font-semibold tabular-nums shrink-0">{amount}</div>
    </div>
  )
  if (line.href) {
    return (
      <Link to={line.href} className="block hover:bg-muted/30 rounded-md px-1 -mx-1 transition-colors">
        {body}
      </Link>
    )
  }
  return <div className="px-1 -mx-1">{body}</div>
}

function SectionCard({
  title,
  icon: Icon,
  total,
  mask,
  locale,
  currency,
  children,
  empty,
  tone,
}: {
  title: string
  icon: React.ElementType
  total: number
  mask: (v: string) => string
  locale: string
  currency: string
  children: React.ReactNode
  empty: string
  tone?: 'pos' | 'neg'
}) {
  const toneClass =
    tone === 'pos'
      ? 'text-emerald-600 dark:text-emerald-400'
      : tone === 'neg'
        ? 'text-rose-600 dark:text-rose-400'
        : ''
  return (
    <section className="rounded-xl border border-border bg-card p-4 sm:p-5 shadow-sm">
      <div className="flex items-center justify-between gap-3 mb-3">
        <div className="flex items-center gap-2">
          <div className="size-8 rounded-lg bg-muted flex items-center justify-center">
            <Icon className="size-4 text-foreground" />
          </div>
          <h2 className="text-sm font-semibold tracking-tight">{title}</h2>
        </div>
        <div className={`text-sm font-semibold tabular-nums ${toneClass}`}>
          {mask(formatCurrency(total, currency, locale))}
        </div>
      </div>
      <div>{children || <p className="text-sm text-muted-foreground py-4 text-center">{empty}</p>}</div>
    </section>
  )
}

export default function ProfitLossPage() {
  const { t } = useTranslation()
  const { mask } = usePrivacyMode()
  const { user } = useAuth()
  const locale = useDisplayLocale()
  const userCurrency = user?.preferences?.currency_display ?? 'USD'
  const { activeAccountIds } = useCollectionFilter()

  const currentYear = new Date().getFullYear()
  const [year, setYear] = useState(currentYear)
  const [prefs, setPrefs] = useState<PlPrefs>(() => loadPrefs())
  const [assumptionsOpen, setAssumptionsOpen] = useState(false)

  useEffect(() => {
    savePrefs(prefs)
  }, [prefs])

  const { data, isLoading, isError } = useQuery<ProfitLossResponse>({
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
        accountIds: activeAccountIds ?? undefined,
      }),
  })

  const currency = data?.currency ?? userCurrency

  const ytdIncomeLines = useMemo(
    () => (data?.ytd_lines ?? []).filter((l) => l.section === 'income'),
    [data],
  )
  const ytdExpenseLines = useMemo(
    () => (data?.ytd_lines ?? []).filter((l) => l.section === 'expense'),
    [data],
  )
  const projIncomeLines = useMemo(
    () => (data?.projection_lines ?? []).filter((l) => l.section === 'income'),
    [data],
  )
  const projExpenseLines = useMemo(
    () => (data?.projection_lines ?? []).filter((l) => l.section === 'expense' || l.section === 'tax'),
    [data],
  )

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 pb-16">
      <PageHeader
        section={t('profitLoss.section')}
        title={t('profitLoss.title')}
        action={
          <div className="flex flex-wrap items-center gap-2">
            <div className="flex items-center gap-2">
              <Label className="text-xs text-muted-foreground whitespace-nowrap">
                {t('profitLoss.year')}
              </Label>
              <Input
                type="number"
                className="w-24 h-9"
                value={year}
                min={2000}
                max={2100}
                onChange={(e) => setYear(Number(e.target.value) || currentYear)}
              />
              {year !== currentYear && (
                <Button type="button" variant="ghost" size="sm" onClick={() => setYear(currentYear)}>
                  {t('profitLoss.thisYear')}
                </Button>
              )}
            </div>
            <Popover open={assumptionsOpen} onOpenChange={setAssumptionsOpen}>
              <PopoverTrigger asChild>
                <Button type="button" variant="outline" size="sm" className="gap-1.5">
                  <Settings2 className="size-3.5" />
                  {t('profitLoss.assumptions')}
                </Button>
              </PopoverTrigger>
              <PopoverContent align="end" className="w-80 space-y-4">
                <div>
                  <h3 className="text-sm font-semibold">{t('profitLoss.assumptionsTitle')}</h3>
                  <p className="text-xs text-muted-foreground mt-1">
                    {t('profitLoss.assumptionsHint')}
                  </p>
                </div>
                <div className="space-y-2">
                  <Label className="text-xs">{t('profitLoss.incomeGrowth')}</Label>
                  <Input
                    type="number"
                    value={prefs.income_growth_pct}
                    onChange={(e) =>
                      setPrefs((p) => ({ ...p, income_growth_pct: Number(e.target.value) || 0 }))
                    }
                  />
                </div>
                <div className="space-y-2">
                  <Label className="text-xs">{t('profitLoss.expenseGrowth')}</Label>
                  <Input
                    type="number"
                    value={prefs.expense_growth_pct}
                    onChange={(e) =>
                      setPrefs((p) => ({ ...p, expense_growth_pct: Number(e.target.value) || 0 }))
                    }
                  />
                </div>
                <div className="flex items-center justify-between gap-3">
                  <Label className="text-xs">{t('profitLoss.includeTax')}</Label>
                  <Switch
                    checked={prefs.include_tax}
                    onCheckedChange={(checked) => setPrefs((p) => ({ ...p, include_tax: checked }))}
                  />
                </div>
                {prefs.include_tax && (
                  <div className="space-y-2">
                    <Label className="text-xs">{t('profitLoss.taxRate')}</Label>
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
                <div className="rounded-lg bg-muted/50 p-3 space-y-2">
                  {(data?.assumptions ?? []).map((a) => (
                    <div key={a.key} className="text-xs">
                      <div className="font-medium text-foreground">
                        {a.label}: <span className="font-normal text-muted-foreground">{a.value}</span>
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
          <div className="grid gap-4 md:grid-cols-2">
            <Skeleton className="h-64 w-full rounded-xl" />
            <Skeleton className="h-64 w-full rounded-xl" />
          </div>
        </div>
      )}

      {isError && (
        <div className="rounded-xl border border-border bg-card p-8 text-center">
          <p className="font-medium">{t('profitLoss.loadError')}</p>
          <p className="text-sm text-muted-foreground mt-1">{t('profitLoss.loadErrorHint')}</p>
        </div>
      )}

      {!isLoading && !isError && data && (
        <>
          <div className="rounded-xl border border-border bg-gradient-to-br from-card to-muted/30 p-5 sm:p-6 mb-6">
            <div className="flex items-start justify-between gap-4 flex-wrap">
              <div>
                <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                  {t('profitLoss.ytdNet')}
                </p>
                <p className="text-3xl sm:text-4xl font-semibold tracking-tight mt-1 tabular-nums">
                  {mask(formatCurrency(data.totals.ytd_net, currency, locale))}
                </p>
                <p className="text-xs text-muted-foreground mt-2">
                  {t('profitLoss.ytdRange', { start: data.ytd_start, end: data.ytd_end })}
                  {' · '}
                  {t('profitLoss.method', { method: data.projection_method })}
                </p>
              </div>
              <div className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm">
                <div>
                  <p className="text-xs text-muted-foreground">{t('profitLoss.projectedNet')}</p>
                  <p className="font-semibold tabular-nums">
                    {mask(formatCurrency(data.totals.projected_net_after_tax, currency, locale))}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">{t('profitLoss.projectedTax')}</p>
                  <p className="font-semibold tabular-nums text-rose-600 dark:text-rose-400">
                    {mask(formatCurrency(data.totals.projected_tax, currency, locale))}
                  </p>
                </div>
              </div>
            </div>
          </div>

          <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
            <TrendingUp className="size-4" />
            {t('profitLoss.ytdSection')}
          </h3>
          <div className="grid gap-4 lg:grid-cols-2 mb-8">
            <SectionCard
              title={t('profitLoss.income')}
              icon={ArrowUpRight}
              total={data.totals.ytd_income}
              mask={mask}
              locale={locale}
              currency={currency}
              empty={t('profitLoss.emptyIncome')}
              tone="pos"
            >
              {ytdIncomeLines.map((line) => (
                <LineRow key={line.key} line={line} mask={mask} locale={locale} currency={currency} />
              ))}
            </SectionCard>
            <SectionCard
              title={t('profitLoss.expenses')}
              icon={ArrowDownRight}
              total={data.totals.ytd_expenses}
              mask={mask}
              locale={locale}
              currency={currency}
              empty={t('profitLoss.emptyExpenses')}
              tone="neg"
            >
              {ytdExpenseLines.map((line) => (
                <LineRow key={line.key} line={line} mask={mask} locale={locale} currency={currency} />
              ))}
            </SectionCard>
          </div>

          <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
            <LineChart className="size-4" />
            {t('profitLoss.projectionSection')}
          </h3>
          <div className="grid gap-4 lg:grid-cols-2 mb-6">
            <SectionCard
              title={t('profitLoss.projectedIncome')}
              icon={ArrowUpRight}
              total={data.totals.projected_income}
              mask={mask}
              locale={locale}
              currency={currency}
              empty={t('profitLoss.emptyIncome')}
              tone="pos"
            >
              {projIncomeLines.map((line) => (
                <LineRow key={line.key} line={line} mask={mask} locale={locale} currency={currency} />
              ))}
            </SectionCard>
            <SectionCard
              title={t('profitLoss.projectedExpenses')}
              icon={ArrowDownRight}
              total={data.totals.projected_expenses + data.totals.projected_tax}
              mask={mask}
              locale={locale}
              currency={currency}
              empty={t('profitLoss.emptyExpenses')}
              tone="neg"
            >
              {projExpenseLines.map((line) => (
                <LineRow key={line.key} line={line} mask={mask} locale={locale} currency={currency} />
              ))}
            </SectionCard>
          </div>

          <section className="rounded-xl border border-dashed border-border bg-card/50 p-4 sm:p-5">
            <h2 className="text-sm font-semibold mb-2">{t('profitLoss.gapsTitle')}</h2>
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
