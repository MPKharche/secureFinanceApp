import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery } from '@tanstack/react-query'
import { Scale, Settings2 } from 'lucide-react'
import { reports } from '@/lib/api'
import { localDateString } from '@/lib/date-utils'
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
import { BalanceSheetT } from '@/components/reports/balance-sheet-t'
import { useAuth } from '@/contexts/auth-context'
import { useCollectionFilter } from '@/contexts/collection-filter-context'
import { useDisplayLocale } from '@/hooks/use-display-locale'
import { usePrivacyMode } from '@/hooks/use-privacy-mode'
import type { BalanceSheetResponse } from '@/types'

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

          <BalanceSheetT
            lines={data.lines}
            totals={data.totals}
            mask={mask}
            locale={locale}
            currency={currency}
          />

          {(data.gaps ?? []).length > 0 && (
            <section className="rounded-xl border border-dashed border-border bg-card/50 p-4 sm:p-5 mt-4">
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
