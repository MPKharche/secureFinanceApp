import { useQuery } from '@tanstack/react-query'
import { formatCurrency } from '@/lib/format'
import {
  FrozenScrollTable,
  FrozenTd,
  FrozenTh,
} from '@/components/ui/frozen-scroll-table'

async function fetchBreakdown(accountId: string) {
  const response = await fetch(`/api/v1/loans/${accountId}/breakdown?group_by=year`, {
    headers: {
      Authorization: `Bearer ${localStorage.getItem('token')}`,
      'X-Workspace-Id': localStorage.getItem('workspace_id') || '',
    },
  })
  if (!response.ok) throw new Error('Failed to fetch breakdown')
  return response.json() as Promise<
    Array<{
      period: string
      principal_component: number
      interest_component: number
      total_paid: number
      prepayments: number
    }>
  >
}

function tone(n: number, invert = false) {
  if (!n) return 'text-foreground'
  const good = invert ? n < 0 : n > 0
  return good
    ? 'text-emerald-700 dark:text-emerald-300'
    : 'text-rose-700 dark:text-rose-300'
}

export function LoanAnalyticsCharts({
  accountId,
  currency = 'USD',
  locale = 'en-US',
}: {
  accountId: string
  currency?: string
  locale?: string
}) {
  const { data, isLoading, error } = useQuery({
    queryKey: ['loan-breakdown', accountId],
    queryFn: () => fetchBreakdown(accountId),
  })

  if (isLoading) {
    return <div className="py-8 text-center text-muted-foreground">Loading analysis…</div>
  }
  if (error) {
    return <div className="py-8 text-center text-destructive">Could not load analysis</div>
  }
  if (!data?.length) {
    return <div className="py-8 text-center text-muted-foreground">No year rows yet</div>
  }

  const totals = data.reduce(
    (acc, row) => {
      acc.principal += row.principal_component || 0
      acc.interest += row.interest_component || 0
      acc.total += row.total_paid || 0
      acc.prepay += row.prepayments || 0
      return acc
    },
    { principal: 0, interest: 0, total: 0, prepay: 0 },
  )

  return (
    <div className="space-y-3">
      <FrozenScrollTable maxHeight="70vh" className="text-sm">
        <thead>
          <tr>
            <FrozenTh stickyLabel className="text-xs">
              Year
            </FrozenTh>
            <FrozenTh align="right" className="text-xs">
              Principal
            </FrozenTh>
            <FrozenTh align="right" className="text-xs">
              Interest
            </FrozenTh>
            <FrozenTh align="right" className="text-xs">
              Total paid
            </FrozenTh>
            <FrozenTh align="right" className="text-xs">
              Prepay
            </FrozenTh>
            <FrozenTh align="right" className="text-xs">
              Interest share
            </FrozenTh>
          </tr>
        </thead>
        <tbody>
          {data.map((row) => {
            const share =
              row.total_paid > 0 ? (row.interest_component / row.total_paid) * 100 : 0
            return (
              <tr key={row.period} className="hover:bg-muted/40">
                <FrozenTd stickyLabel className="font-medium">
                  {row.period}
                </FrozenTd>
                <FrozenTd align="right" className="tabular-nums">
                  {formatCurrency(row.principal_component, currency, locale)}
                </FrozenTd>
                <FrozenTd
                  align="right"
                  className={`tabular-nums ${tone(row.interest_component, true)}`}
                >
                  {formatCurrency(row.interest_component, currency, locale)}
                </FrozenTd>
                <FrozenTd align="right" className="tabular-nums font-medium">
                  {formatCurrency(row.total_paid, currency, locale)}
                </FrozenTd>
                <FrozenTd
                  align="right"
                  className={`tabular-nums ${row.prepayments > 0 ? 'text-emerald-700 dark:text-emerald-300' : 'text-muted-foreground'}`}
                >
                  {row.prepayments > 0
                    ? formatCurrency(row.prepayments, currency, locale)
                    : '—'}
                </FrozenTd>
                <FrozenTd align="right" className="tabular-nums text-muted-foreground">
                  {share.toFixed(1)}%
                </FrozenTd>
              </tr>
            )
          })}
          <tr className="bg-muted/60 font-medium">
            <FrozenTd stickyLabel className="bg-muted/60">
              Total
            </FrozenTd>
            <FrozenTd align="right" className="tabular-nums">
              {formatCurrency(totals.principal, currency, locale)}
            </FrozenTd>
            <FrozenTd align="right" className="tabular-nums">
              {formatCurrency(totals.interest, currency, locale)}
            </FrozenTd>
            <FrozenTd align="right" className="tabular-nums">
              {formatCurrency(totals.total, currency, locale)}
            </FrozenTd>
            <FrozenTd align="right" className="tabular-nums">
              {totals.prepay > 0 ? formatCurrency(totals.prepay, currency, locale) : '—'}
            </FrozenTd>
            <FrozenTd align="right" className="tabular-nums text-muted-foreground">
              {totals.total > 0 ? ((totals.interest / totals.total) * 100).toFixed(1) : '0.0'}%
            </FrozenTd>
          </tr>
        </tbody>
      </FrozenScrollTable>
    </div>
  )
}
