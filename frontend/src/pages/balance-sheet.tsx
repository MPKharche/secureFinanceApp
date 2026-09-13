import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useQuery } from '@tanstack/react-query'
import {
  Building2,
  CircleHelp,
  Landmark,
  Scale,
  Settings2,
  Wallet,
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
    <div className="flex items-start justify-between gap-3 py-2.5 border-b border-border/60 last:border-0">
      <div className="min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-sm font-medium text-foreground truncate">{line.label}</span>
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
        {line.account_type && (
          <p className="text-xs text-muted-foreground mt-0.5 capitalize">
            {line.account_type.replace(/_/g, ' ')}
          </p>
        )}
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
}: {
  title: string
  icon: React.ElementType
  total: number
  mask: (v: string) => string
  locale: string
  currency: string
  children: React.ReactNode
  empty: string
}) {
  return (
    <section className="rounded-xl border border-border bg-card p-4 sm:p-5 shadow-sm">
      <div className="flex items-center justify-between gap-3 mb-3">
        <div className="flex items-center gap-2">
          <div className="size-8 rounded-lg bg-muted flex items-center justify-center">
            <Icon className="size-4 text-foreground" />
          </div>
          <h2 className="text-sm font-semibold tracking-tight">{title}</h2>
        </div>
        <div className="text-sm font-semibold tabular-nums">
          {mask(formatCurrency(total, currency, locale))}
        </div>
      </div>
      <div>{children || <p className="text-sm text-muted-foreground py-4 text-center">{empty}</p>}</div>
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
  const investLines = useMemo(
    () => (data?.lines ?? []).filter((l) => l.group === 'investments'),
    [data],
  )
  const loanLines = useMemo(
    () => (data?.lines ?? []).filter((l) => l.group === 'loans' || l.group === 'other_liabilities'),
    [data],
  )

  const isToday = asOf === localDateString()
  const hasApprox = (data?.lines ?? []).some((l) => l.fidelity !== 'as_of')

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
          <Skeleton className="h-28 w-full rounded-xl" />
          <div className="grid gap-4 md:grid-cols-2">
            <Skeleton className="h-64 w-full rounded-xl" />
            <Skeleton className="h-64 w-full rounded-xl" />
          </div>
        </div>
      )}

      {isError && (
        <div className="rounded-xl border border-border bg-card p-8 text-center">
          <p className="font-medium">{t('balanceSheet.loadError')}</p>
          <p className="text-sm text-muted-foreground mt-1">{t('balanceSheet.loadErrorHint')}</p>
        </div>
      )}

      {!isLoading && !isError && data && (
        <>
          <div className="rounded-xl border border-border bg-gradient-to-br from-card to-muted/30 p-5 sm:p-6 mb-6">
            <div className="flex items-start justify-between gap-4 flex-wrap">
              <div>
                <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                  {t('balanceSheet.netWorth')}
                </p>
                <p className="text-3xl sm:text-4xl font-semibold tracking-tight mt-1 tabular-nums">
                  {mask(formatCurrency(data.totals.net_worth, currency, locale))}
                </p>
                <p className="text-xs text-muted-foreground mt-2">
                  {t('balanceSheet.asOfDate', { date: data.as_of })}
                  {hasApprox ? ` · ${t('balanceSheet.someApprox')}` : ''}
                </p>
              </div>
              <div className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm">
                <div>
                  <p className="text-xs text-muted-foreground">{t('balanceSheet.totalAssets')}</p>
                  <p className="font-semibold tabular-nums text-emerald-600 dark:text-emerald-400">
                    {mask(formatCurrency(data.totals.assets, currency, locale))}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">{t('balanceSheet.totalLiabilities')}</p>
                  <p className="font-semibold tabular-nums text-rose-600 dark:text-rose-400">
                    {mask(formatCurrency(data.totals.liabilities, currency, locale))}
                  </p>
                </div>
              </div>
            </div>
          </div>

          <div className="grid gap-4 lg:grid-cols-2 mb-6">
            <div className="space-y-4">
              <SectionCard
                title={t('balanceSheet.cashAccounts')}
                icon={Wallet}
                total={data.totals.cash_accounts}
                mask={mask}
                locale={locale}
                currency={currency}
                empty={t('balanceSheet.emptyCash')}
              >
                {cashLines.map((line) => (
                  <LineRow key={line.key} line={line} mask={mask} locale={locale} currency={currency} />
                ))}
              </SectionCard>
              <SectionCard
                title={t('balanceSheet.investments')}
                icon={Landmark}
                total={data.totals.investments}
                mask={mask}
                locale={locale}
                currency={currency}
                empty={t('balanceSheet.emptyInvestments')}
              >
                {investLines.map((line) => (
                  <LineRow key={line.key} line={line} mask={mask} locale={locale} currency={currency} />
                ))}
              </SectionCard>
            </div>
            <div className="space-y-4">
              <SectionCard
                title={t('balanceSheet.liabilities')}
                icon={Building2}
                total={data.totals.liabilities}
                mask={mask}
                locale={locale}
                currency={currency}
                empty={t('balanceSheet.emptyLiabilities')}
              >
                {loanLines.map((line) => (
                  <LineRow key={line.key} line={line} mask={mask} locale={locale} currency={currency} />
                ))}
              </SectionCard>
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
            </div>
          </div>
        </>
      )}

      {!isLoading && !isError && data && data.lines.length === 0 && (
        <div className="rounded-xl border border-border bg-card p-10 text-center">
          <p className="font-medium">{t('balanceSheet.empty')}</p>
          <p className="text-sm text-muted-foreground mt-1">{t('balanceSheet.emptyHint')}</p>
        </div>
      )}
    </div>
  )
}
