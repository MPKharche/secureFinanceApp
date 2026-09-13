import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { CircleHelp } from 'lucide-react'
import { formatCurrency } from '@/lib/format'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import type { BalanceSheetLine } from '@/types'
import { cn } from '@/lib/utils'

export function isInsuranceLine(line: BalanceSheetLine): boolean {
  const meta = line.meta as Record<string, unknown> | null | undefined
  if (meta && meta.insurance === true) return true
  const type = (line.account_type || '').toLowerCase()
  return type.includes('insurance') || type.includes('policy')
}

export function isPropertyLine(line: BalanceSheetLine): boolean {
  const type = (line.account_type || '').toLowerCase()
  return (
    type.includes('real_estate') ||
    type.includes('property') ||
    type.includes('home') ||
    type.includes('house')
  )
}

function fidelityBadge(fidelity: string, t: (key: string) => string) {
  if (fidelity === 'as_of') return t('balanceSheet.fidelityAsOf')
  if (fidelity === 'reconstructed') return t('balanceSheet.fidelityReconstructed')
  return t('balanceSheet.fidelityApprox')
}

export function BsLineRow({
  line,
  mask,
  locale,
  currency,
  compact = false,
}: {
  line: BalanceSheetLine
  mask: (v: string) => string
  locale: string
  currency: string
  compact?: boolean
}) {
  const { t } = useTranslation()
  const amount = mask(formatCurrency(line.value, currency, locale))
  const body = (
    <div
      className={cn(
        'flex items-start justify-between gap-3 border-b border-border/50 last:border-0',
        compact ? 'py-1.5' : 'py-2',
      )}
    >
      <div className="min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className={cn('text-foreground truncate', compact ? 'text-xs' : 'text-sm')}>
            {line.label}
          </span>
          {!compact && (
            <>
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
            </>
          )}
        </div>
      </div>
      <div className={cn('font-medium tabular-nums shrink-0', compact ? 'text-xs' : 'text-sm')}>
        {amount}
      </div>
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

export function BsSubGroup({
  title,
  lines,
  empty,
  mask,
  locale,
  currency,
  tone = 'neutral',
  compact = false,
  defaultExpanded = true,
}: {
  title: string
  lines: BalanceSheetLine[]
  empty: string
  mask: (v: string) => string
  locale: string
  currency: string
  tone?: 'liability' | 'asset' | 'neutral'
  compact?: boolean
  defaultExpanded?: boolean
}) {
  const [open, setOpen] = useState(defaultExpanded)
  const subtotal = lines.reduce((s, l) => s + l.value, 0)
  return (
    <div className={cn(compact ? 'mb-3 last:mb-0' : 'mb-4 last:mb-0')}>
      <div className="flex items-baseline justify-between gap-2 mb-1">
        <button
          type="button"
          className={cn(
            'font-semibold uppercase tracking-wider inline-flex items-center gap-1',
            compact ? 'text-[10px]' : 'text-xs',
            tone === 'liability' && 'text-rose-700 dark:text-rose-300',
            tone === 'asset' && 'text-emerald-700 dark:text-emerald-300',
            tone === 'neutral' && 'text-foreground/70',
          )}
          onClick={() => setOpen((v) => !v)}
          aria-expanded={open}
        >
          <span className="text-[10px] font-bold opacity-70">{open ? '−' : '+'}</span>
          {title}
        </button>
        {lines.length > 0 && (
          <span className="text-[11px] tabular-nums text-muted-foreground">
            {mask(formatCurrency(subtotal, currency, locale))}
          </span>
        )}
      </div>
      {open &&
        (lines.length === 0 ? (
          <p className={cn('text-muted-foreground', compact ? 'text-xs py-1' : 'text-sm py-2')}>
            {empty}
          </p>
        ) : (
          <div>
            {lines.map((line) => (
              <BsLineRow
                key={line.key}
                line={line}
                mask={mask}
                locale={locale}
                currency={currency}
                compact={compact}
              />
            ))}
          </div>
        ))}
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
  compact,
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
  compact?: boolean
  children: React.ReactNode
}) {
  const isLeft = side === 'left'
  return (
    <section
      className={cn('flex flex-col min-h-0 bg-card', isLeft && 'md:border-r md:border-border')}
      aria-label={`${title}: ${subtitle}`}
    >
      <header
        className={cn(
          'border-b',
          compact ? 'px-3 sm:px-4 pt-3 pb-2' : 'px-4 sm:px-5 pt-4 pb-3',
          isLeft
            ? 'border-rose-200/70 dark:border-rose-900/50 bg-rose-50/40 dark:bg-rose-950/20'
            : 'border-emerald-200/70 dark:border-emerald-900/50 bg-emerald-50/40 dark:bg-emerald-950/20',
        )}
      >
        <p className="text-[11px] font-semibold tracking-wide text-foreground/70">{subtitle}</p>
        <h2
          className={cn(
            'font-semibold tracking-tight mt-0.5',
            compact ? 'text-sm' : 'text-base',
            isLeft ? 'text-rose-800 dark:text-rose-300' : 'text-emerald-800 dark:text-emerald-300',
          )}
        >
          {title}
        </h2>
      </header>
      <div className={cn('flex-1', compact ? 'px-3 sm:px-4 py-3' : 'px-4 sm:px-5 py-4')}>
        {children}
      </div>
      <footer
        className={cn(
          'mt-auto border-t-2',
          compact ? 'px-3 sm:px-4 py-2.5' : 'px-4 sm:px-5 py-3',
          isLeft
            ? 'border-rose-300/80 dark:border-rose-800 bg-rose-50/50 dark:bg-rose-950/30'
            : 'border-emerald-300/80 dark:border-emerald-800 bg-emerald-50/50 dark:bg-emerald-950/30',
        )}
      >
        <div className="flex items-baseline justify-between gap-3">
          <span className={cn('font-semibold', compact ? 'text-xs' : 'text-sm')}>{totalLabel}</span>
          <span
            className={cn(
              'font-semibold tabular-nums',
              compact ? 'text-sm' : 'text-base',
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

export function BalanceSheetT({
  lines,
  totals,
  mask,
  locale,
  currency,
  compact = false,
  showNetWorth = true,
}: {
  lines: BalanceSheetLine[]
  totals: { assets: number; liabilities: number; net_worth: number }
  mask: (v: string) => string
  locale: string
  currency: string
  compact?: boolean
  showNetWorth?: boolean
}) {
  const { t } = useTranslation()
  const cashLines = lines.filter((l) => l.group === 'cash_accounts')
  const propertyLines = lines.filter(
    (l) => l.group === 'investments' && isPropertyLine(l) && !isInsuranceLine(l),
  )
  const insuranceLines = lines.filter(
    (l) => l.group === 'investments' && isInsuranceLine(l),
  )
  const investmentLines = lines.filter(
    (l) =>
      l.group === 'investments' && !isInsuranceLine(l) && !isPropertyLine(l),
  )
  const loanLines = lines.filter((l) => l.group === 'loans')
  const creditLines = lines.filter((l) => l.group === 'other_liabilities')
  const savingsBuffer = cashLines.reduce((s, l) => s + l.value, 0)

  return (
    <div className="rounded-xl border border-border shadow-sm overflow-hidden">
      <div className="grid grid-cols-1 md:grid-cols-2 md:items-stretch">
        {/* LEFT — What you owe */}
        <TColumn
          side="left"
          title={t('balanceSheet.liabilitiesCol')}
          subtitle={t('balanceSheet.whatYouOwe')}
          total={totals.liabilities}
          totalLabel={t('balanceSheet.totalLiabilitiesLabel')}
          mask={mask}
          locale={locale}
          currency={currency}
          compact={compact}
        >
          <BsSubGroup
            title={t('balanceSheet.loans')}
            lines={loanLines}
            empty={t('balanceSheet.emptyLoans')}
            mask={mask}
            locale={locale}
            currency={currency}
            tone="liability"
            compact={compact}
          />
          <BsSubGroup
            title={t('balanceSheet.creditCards')}
            lines={creditLines}
            empty={t('balanceSheet.emptyCredit')}
            mask={mask}
            locale={locale}
            currency={currency}
            tone="liability"
            compact={compact}
          />
        </TColumn>

        {/* RIGHT — What you own */}
        <TColumn
          side="right"
          title={t('balanceSheet.assets')}
          subtitle={t('balanceSheet.whatYouOwn')}
          total={totals.assets}
          totalLabel={t('balanceSheet.totalAssetsLabel')}
          mask={mask}
          locale={locale}
          currency={currency}
          compact={compact}
        >
          <BsSubGroup
            title={t('balanceSheet.cashAccounts')}
            lines={cashLines}
            empty={t('balanceSheet.emptyCash')}
            mask={mask}
            locale={locale}
            currency={currency}
            tone="asset"
            compact={compact}
          />
          <BsSubGroup
            title={t('balanceSheet.property')}
            lines={propertyLines}
            empty={t('balanceSheet.emptyProperty')}
            mask={mask}
            locale={locale}
            currency={currency}
            tone="asset"
            compact={compact}
          />
          <BsSubGroup
            title={t('balanceSheet.investments')}
            lines={investmentLines}
            empty={t('balanceSheet.emptyInvestments')}
            mask={mask}
            locale={locale}
            currency={currency}
            tone="asset"
            compact={compact}
          />
          <BsSubGroup
            title={t('balanceSheet.insuranceValue')}
            lines={insuranceLines}
            empty={t('balanceSheet.emptyInsurance')}
            mask={mask}
            locale={locale}
            currency={currency}
            tone="asset"
            compact={compact}
          />
        </TColumn>
      </div>

      {showNetWorth && (
        <div
          className={cn(
            'border-t border-border bg-gradient-to-br from-card via-muted/20 to-card',
            compact ? 'px-3 sm:px-4 py-3' : 'px-4 sm:px-6 py-5',
          )}
        >
          <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-2">
            <div>
              <p className="text-[11px] font-medium text-muted-foreground uppercase tracking-wide">
                {t('balanceSheet.yourNetWorth')}
              </p>
              {savingsBuffer > 0 && (
                <p className="text-[10px] text-muted-foreground mt-0.5 tabular-nums">
                  {t('balanceSheet.savingsBuffer')}{' '}
                  {mask(formatCurrency(savingsBuffer, currency, locale))}
                </p>
              )}
            </div>
            <p
              className={cn(
                'font-semibold tracking-tight tabular-nums',
                compact ? 'text-2xl' : 'text-3xl sm:text-4xl',
                totals.net_worth >= 0
                  ? 'text-foreground'
                  : 'text-rose-700 dark:text-rose-400',
              )}
            >
              {mask(formatCurrency(totals.net_worth, currency, locale))}
            </p>
          </div>
        </div>
      )}
    </div>
  )
}
