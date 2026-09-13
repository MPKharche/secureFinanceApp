import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useQuery } from '@tanstack/react-query'
import {
  CircleHelp,
  Scale,
  Settings2,
} from 'lucide-react'
import { reports } from '@/lib/api'
import { localDateString } from '@/lib/date-utils'
import { formatCurrency } from '@/lib/format'
import { PageHeader } from '@/components/page-header'
import { DatePickerInput } from '@/components/ui/date-picker-input'
import { Skeleton } from '@/components/ui/skeleton'
import { Button } from '@/components/ui/button'
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
import type { BalanceSheetLine, BalanceSheetResponse } from '@/types'
import { cn } from '@/lib/utils'

const PREFS_KEY = 'securo.balanceSheet.prefs'

type InsuranceBasis = 'recorded' | 'sad' | 'sv'

type BsPrefs = {
  insurance_value_basis: InsuranceBasis
}

function loadPrefs(): BsPrefs {
  try {
    const raw = localStorage.getItem(PREFS_KEY)
    if (!raw) return { insurance_value_basis: 'recorded' }
    const parsed = JSON.parse(raw) as Partial<BsPrefs>
    const basis = parsed.insurance_value_basis
    if (basis === 'sad' || basis === 'sv' || basis === 'recorded') {
      return { insurance_value_basis: basis }
    }
  } catch {
    /* ignore */
  }
  return { insurance_value_basis: 'recorded' }
}

function savePrefs(prefs: BsPrefs) {
  localStorage.setItem(PREFS_KEY, JSON.stringify(prefs))
}

function fidelityBadge(fidelity: string, t: (key: string) => string) {
  if (fidelity === 'as_of') return t('balanceSheet.fidelityAsOf')
  if (fidelity === 'reconstructed') return t('balanceSheet.fidelityReconstructed')
  return t('balanceSheet.fidelityApprox')
}

function isInsuranceLine(line: BalanceSheetLine): boolean {
  const meta = line.meta as Record<string, unknown> | null | undefined
  if (meta && meta.insurance === true) return true
  const type = (line.account_type || '').toLowerCase()
  return type.includes('insurance') || type.includes('policy')
}

function LineRow({
  line,
  mask,
  locale,
  currency,
}: {
  line: BalanceSheetLine
  mask: (v: string) => string
  locale: string
  currency: string
}) {
  const { t } = useTranslation()
  const amount = mask(formatCurrency(line.value, currency, locale))
  const body = (
    <div className="flex items-start justify-between gap-3 py-2 border-b border-border/50 last:border-0">
      <div className="min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-sm text-foreground truncate">{line.label}</span>
          <span className="text-[10px] uppercase tracking-wide px-1.5 py-0.5 rounded bg-muted text-muted-foreground">
            {fidelityBadge(line.fidelity, t)}
          </span>
          {line.fidelity_note && (
            <Popover>
              <PopoverTrigger asChild>
                <button
                  type="button"
                  className="text-muted-foreground hover:text-foreground"
                  aria-label={t('balanceSheet.fidelityHelp')}
                >
                  <CircleHelp className="size-3.5" />
                </button>
              </PopoverTrigger>
              <PopoverContent className="max-w-xs text-sm" align="start">
                {line.fidelity_note}
              </PopoverContent>
            </Popover>
          )}
        </div>
      </div>
      <div className="text-sm font-medium tabular-nums shrink-0">{amount}</div>
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

function SubGroup({
  title,
  lines,
  empty,
  mask,
  locale,
  currency,
  tone = 'neutral',
}: {
  title: string
  lines: BalanceSheetLine[]
  empty: string
  mask: (v: string) => string
  locale: string
  currency: string
  tone?: 'liability' | 'asset' | 'neutral'
}) {
  const subtotal = lines.reduce((s, l) => s + l.value, 0)
  return (
    <div className="mb-4 last:mb-0">
      <div className="flex items-baseline justify-between gap-2 mb-1.5">
        <h3
          className={cn(
            'text-xs font-semibold uppercase tracking-wider',
            tone === 'liability' && 'text-rose-700 dark:text-rose-400',
            tone === 'asset' && 'text-emerald-700 dark:text-emerald-400',
            tone === 'neutral' && 'text-muted-foreground',
          )}
        >
          {title}
        </h3>
        {lines.length > 0 && (
          <span className="text-xs tabular-nums text-muted-foreground">
            {mask(formatCurrency(subtotal, currency, locale))}
          </span>
        )}
      </div>
      {lines.length === 0 ? (
        <p className="text-sm text-muted-foreground/80 py-2">{empty}</p>
      ) : (
        <div>
          {lines.map((line) => (
            <LineRow key={line.key} line={line} mask={mask} locale={locale} currency={currency} />
          ))}
        </div>
      )}
    </div>
  )
}

function TColumn({
  side,
  title,
  subtitle,
  total,
  totalLabel,
  mask,
  locale,
  currency,
  children,
}: {
  side: 'left' | 'right'
  title: string
  subtitle: string
  total: number
  totalLabel: string
  mask: (v: string) => string
  locale: string
  currency: string
  children: React.ReactNode
}) {
  const isLeft = side === 'left'
  return (
    <section
      className={cn(
        'flex flex-col min-h-0 bg-card',
        isLeft
          ? 'md:border-r md:border-border'
          : '',
      )}
      aria-label={`${title}: ${subtitle}`}
    >
      <header
        className={cn(
          'px-4 sm:px-5 pt-4 pb-3 border-b',
          isLeft
            ? 'border-rose-200/70 dark:border-rose-900/50 bg-rose-50/40 dark:bg-rose-950/20'
            : 'border-emerald-200/70 dark:border-emerald-900/50 bg-emerald-50/40 dark:bg-emerald-950/20',
        )}
      >
        <p className="text-[11px] font-medium text-muted-foreground tracking-wide">
          {subtitle}
        </p>
        <h2
          className={cn(
            'text-base font-semibold tracking-tight mt-0.5',
            isLeft ? 'text-rose-800 dark:text-rose-300' : 'text-emerald-800 dark:text-emerald-300',
          )}
        >
          {title}
        </h2>
      </header>

      <div className="flex-1 px-4 sm:px-5 py-4">{children}</div>

      <footer
        className={cn(
          'mt-auto px-4 sm:px-5 py-3 border-t-2',
          isLeft
            ? 'border-rose-300/80 dark:border-rose-800 bg-rose-50/50 dark:bg-rose-950/30'
            : 'border-emerald-300/80 dark:border-emerald-800 bg-emerald-50/50 dark:bg-emerald-950/30',
        )}
      >
        <div className="flex items-baseline justify-between gap-3">
          <span className="text-sm font-semibold">{totalLabel}</span>
          <span
            className={cn(
              'text-base font-semibold tabular-nums',
              isLeft
                ? 'text-rose-700 dark:text-rose-400'
                : 'text-emerald-700 dark:text-emerald-400',
            )}
          >
            {mask(formatCurrency(total, currency, locale))}
          </span>
        </div>
      </footer>
    </section>
  )
}

export default function BalanceSheetPage() {
  const { t } = useTranslation()
  const { mask } = usePrivacyMode()
  const { user } = useAuth()
  const locale = useDisplayLocale()
  const userCurrency = user?.preferences?.currency_display ?? 'USD'
  const { activeAccountIds, activeWalletIds } = useCollectionFilter()

  const [asOf, setAsOf] = useState(localDateString())
  const [prefs, setPrefs] = useState<BsPrefs>(() => loadPrefs())
  const [assumptionsOpen, setAssumptionsOpen] = useState(false)

  useEffect(() => {
    savePrefs(prefs)
  }, [prefs])

  const { data, isLoading, isError } = useQuery<BalanceSheetResponse>({
    queryKey: [
      'balance-sheet',
      asOf,
      prefs.insurance_value_basis,
      activeAccountIds,
      activeWalletIds,
    ],
    queryFn: () =>
      reports.balanceSheet(
        asOf,
        prefs.insurance_value_basis,
        activeAccountIds ?? undefined,
        activeWalletIds ?? undefined,
      ),
  })

  const currency = data?.currency ?? userCurrency

  const cashLines = useMemo(
    () => (data?.lines ?? []).filter((l) => l.group === 'cash_accounts'),
    [data],
  )
  const investmentLines = useMemo(
    () =>
      (data?.lines ?? []).filter(
        (l) => l.group === 'investments' && !isInsuranceLine(l),
      ),
    [data],
  )
  const insuranceLines = useMemo(
    () =>
      (data?.lines ?? []).filter(
        (l) => l.group === 'investments' && isInsuranceLine(l),
      ),
    [data],
  )
  const loanLines = useMemo(
    () => (data?.lines ?? []).filter((l) => l.group === 'loans'),
    [data],
  )
  const creditLines = useMemo(
    () => (data?.lines ?? []).filter((l) => l.group === 'other_liabilities'),
    [data],
  )

  const isToday = asOf === localDateString()
  const hasApprox = (data?.lines ?? []).some((l) => l.fidelity !== 'as_of')
  const hasLines = (data?.lines?.length ?? 0) > 0

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 pb-16">
      <PageHeader
        section={t('balanceSheet.section')}
        title={t('balanceSheet.title')}
        action={
          <div className="flex flex-wrap items-center gap-2">
            <div className="flex items-center gap-2">
              <Label className="text-xs text-muted-foreground whitespace-nowrap">
                {t('balanceSheet.asOf')}
              </Label>
              <DatePickerInput value={asOf} onChange={setAsOf} />
              {!isToday && (
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => setAsOf(localDateString())}
                >
                  {t('balanceSheet.today')}
                </Button>
              )}
            </div>
            <Popover open={assumptionsOpen} onOpenChange={setAssumptionsOpen}>
              <PopoverTrigger asChild>
                <Button type="button" variant="outline" size="sm" className="gap-1.5">
                  <Settings2 className="size-3.5" />
                  {t('balanceSheet.assumptions')}
                </Button>
              </PopoverTrigger>
              <PopoverContent align="end" className="w-80 space-y-4">
                <div>
                  <h3 className="text-sm font-semibold">{t('balanceSheet.assumptionsTitle')}</h3>
                  <p className="text-xs text-muted-foreground mt-1">
                    {t('balanceSheet.assumptionsHint')}
                  </p>
                </div>
                <div className="space-y-2">
                  <Label className="text-xs">{t('balanceSheet.insuranceBasis')}</Label>
                  <Select
                    value={prefs.insurance_value_basis}
                    onValueChange={(v) =>
                      setPrefs({ insurance_value_basis: v as InsuranceBasis })
                    }
                  >
                    <SelectTrigger className="w-full">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="recorded">{t('balanceSheet.basisRecorded')}</SelectItem>
                      <SelectItem value="sad">{t('balanceSheet.basisSad')}</SelectItem>
                      <SelectItem value="sv">{t('balanceSheet.basisSv')}</SelectItem>
                    </SelectContent>
                  </Select>
                  <p className="text-[11px] text-muted-foreground leading-relaxed">
                    {t('balanceSheet.insuranceBasisHelp')}
                  </p>
                </div>
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
          <Skeleton className="h-24 w-full rounded-xl" />
          <Skeleton className="h-80 w-full rounded-xl" />
        </div>
      )}

      {isError && (
        <div className="rounded-xl border border-border bg-card p-8 text-center">
          <p className="font-medium">{t('balanceSheet.loadError')}</p>
          <p className="text-sm text-muted-foreground mt-1">{t('balanceSheet.loadErrorHint')}</p>
        </div>
      )}

      {!isLoading && !isError && data && !hasLines && (
        <div className="rounded-xl border border-border bg-card p-10 text-center">
          <p className="font-medium">{t('balanceSheet.empty')}</p>
          <p className="text-sm text-muted-foreground mt-1">{t('balanceSheet.emptyHint')}</p>
        </div>
      )}

      {!isLoading && !isError && data && hasLines && (
        <>
          <p className="text-xs text-muted-foreground mb-3">
            {t('balanceSheet.asOfDate', { date: data.as_of })}
            {hasApprox ? ` · ${t('balanceSheet.someApprox')}` : ''}
            {' · '}
            {t('balanceSheet.tHint')}
          </p>

          {/* T-format: LEFT = Liabilities, RIGHT = Assets */}
          <div className="rounded-xl border border-border shadow-sm overflow-hidden mb-4">
            <div className="grid grid-cols-1 md:grid-cols-2 md:items-stretch">
              {/* LEFT — Liabilities (What you owe) */}
              <TColumn
                side="left"
                title={t('balanceSheet.liabilitiesCol')}
                subtitle={t('balanceSheet.whatYouOwe')}
                total={data.totals.liabilities}
                totalLabel={t('balanceSheet.totalLiabilitiesLabel')}
                mask={mask}
                locale={locale}
                currency={currency}
              >
                <SubGroup
                  title={t('balanceSheet.loans')}
                  lines={loanLines}
                  empty={t('balanceSheet.emptyLoans')}
                  mask={mask}
                  locale={locale}
                  currency={currency}
                  tone="liability"
                />
                <SubGroup
                  title={t('balanceSheet.creditCards')}
                  lines={creditLines}
                  empty={t('balanceSheet.emptyCredit')}
                  mask={mask}
                  locale={locale}
                  currency={currency}
                  tone="liability"
                />
              </TColumn>

              {/* RIGHT — Assets (What you own) */}
              <TColumn
                side="right"
                title={t('balanceSheet.assets')}
                subtitle={t('balanceSheet.whatYouOwn')}
                total={data.totals.assets}
                totalLabel={t('balanceSheet.totalAssetsLabel')}
                mask={mask}
                locale={locale}
                currency={currency}
              >
                <SubGroup
                  title={t('balanceSheet.cashAccounts')}
                  lines={cashLines}
                  empty={t('balanceSheet.emptyCash')}
                  mask={mask}
                  locale={locale}
                  currency={currency}
                  tone="asset"
                />
                <SubGroup
                  title={t('balanceSheet.investments')}
                  lines={investmentLines}
                  empty={t('balanceSheet.emptyInvestments')}
                  mask={mask}
                  locale={locale}
                  currency={currency}
                  tone="asset"
                />
                <SubGroup
                  title={t('balanceSheet.insuranceValue')}
                  lines={insuranceLines}
                  empty={t('balanceSheet.emptyInsurance')}
                  mask={mask}
                  locale={locale}
                  currency={currency}
                  tone="asset"
                />
              </TColumn>
            </div>

            {/* Net worth bridge under the T */}
            <div className="border-t border-border bg-gradient-to-br from-card via-muted/20 to-card px-4 sm:px-6 py-5">
              <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-3">
                <div>
                  <p className="text-[11px] font-medium text-muted-foreground uppercase tracking-wide">
                    {t('balanceSheet.yourNetWorth')}
                  </p>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    {t('balanceSheet.netWorthBridge')}
                  </p>
                </div>
                <p
                  className={cn(
                    'text-3xl sm:text-4xl font-semibold tracking-tight tabular-nums',
                    data.totals.net_worth >= 0
                      ? 'text-foreground'
                      : 'text-rose-700 dark:text-rose-400',
                  )}
                >
                  {mask(formatCurrency(data.totals.net_worth, currency, locale))}
                </p>
              </div>
              <div className="mt-4 grid grid-cols-2 gap-3 text-sm max-w-md">
                <div className="rounded-lg bg-emerald-50/60 dark:bg-emerald-950/30 px-3 py-2">
                  <p className="text-[11px] text-muted-foreground">{t('balanceSheet.totalAssets')}</p>
                  <p className="font-semibold tabular-nums text-emerald-700 dark:text-emerald-400">
                    {mask(formatCurrency(data.totals.assets, currency, locale))}
                  </p>
                </div>
                <div className="rounded-lg bg-rose-50/60 dark:bg-rose-950/30 px-3 py-2">
                  <p className="text-[11px] text-muted-foreground">{t('balanceSheet.totalLiabilities')}</p>
                  <p className="font-semibold tabular-nums text-rose-700 dark:text-rose-400">
                    {mask(formatCurrency(data.totals.liabilities, currency, locale))}
                  </p>
                </div>
              </div>
            </div>
          </div>

          {(data.gaps ?? []).length > 0 && (
            <section className="rounded-xl border border-dashed border-border bg-card/50 p-4 sm:p-5">
              <div className="flex items-center gap-2 mb-2">
                <Scale className="size-4 text-muted-foreground" />
                <h2 className="text-sm font-semibold">{t('balanceSheet.gapsTitle')}</h2>
              </div>
              <ul className="text-xs text-muted-foreground space-y-1.5 list-disc pl-4">
                {(data.gaps ?? []).map((g) => (
                  <li key={g}>{g}</li>
                ))}
              </ul>
            </section>
          )}
        </>
      )}
    </div>
  )
}
