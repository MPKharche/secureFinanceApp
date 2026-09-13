import { useQuery } from '@tanstack/react-query'
import { formatCurrency } from '@/lib/format'
import {
  FrozenScrollTable,
  FrozenTd,
  FrozenTh,
} from '@/components/ui/frozen-scroll-table'

interface Entry {
  id: string
  emi_number: number
  due_date: string
  principal_component: number
  interest_component: number
  emi_amount: number
  opening_balance: number
  closing_balance: number
  payment_status: string
}

async function fetchSchedule(accountId: string): Promise<Entry[]> {
  const response = await fetch(`/api/v1/loans/${accountId}/schedule`, {
    headers: {
      Authorization: `Bearer ${localStorage.getItem('token')}`,
      'X-Workspace-Id': localStorage.getItem('workspace_id') || '',
    },
  })
  if (!response.ok) throw new Error('Failed to fetch schedule')
  return response.json()
}

export function LoanScheduleTable({
  accountId,
  currency = 'USD',
  locale = 'en-US',
}: {
  accountId: string
  currency?: string
  locale?: string
}) {
  const { data, isLoading, error } = useQuery({
    queryKey: ['loan-schedule', accountId],
    queryFn: () => fetchSchedule(accountId),
  })
  if (isLoading) return <div className="py-8 text-center text-muted-foreground">Loading schedule…</div>
  if (error) return <div className="py-8 text-center text-destructive">Failed to load schedule</div>
  if (!data?.length) return <div className="py-8 text-center text-muted-foreground">No schedule entries</div>
  return (
    <FrozenScrollTable maxHeight="70vh" className="rounded-md">
      <thead>
        <tr>
          <FrozenTh stickyLabel>#</FrozenTh>
          <FrozenTh>Due</FrozenTh>
          <FrozenTh align="right">Principal</FrozenTh>
          <FrozenTh align="right">Interest</FrozenTh>
          <FrozenTh align="right">EMI</FrozenTh>
          <FrozenTh align="right">Balance</FrozenTh>
          <FrozenTh>Status</FrozenTh>
        </tr>
      </thead>
      <tbody>
        {data.map((e) => (
          <tr key={e.id}>
            <FrozenTd stickyLabel>{e.emi_number}</FrozenTd>
            <FrozenTd>{e.due_date}</FrozenTd>
            <FrozenTd align="right">
              {formatCurrency(Number(e.principal_component), currency, locale)}
            </FrozenTd>
            <FrozenTd align="right">
              {formatCurrency(Number(e.interest_component), currency, locale)}
            </FrozenTd>
            <FrozenTd align="right">
              {formatCurrency(Number(e.emi_amount), currency, locale)}
            </FrozenTd>
            <FrozenTd align="right">
              {formatCurrency(Number(e.closing_balance), currency, locale)}
            </FrozenTd>
            <FrozenTd className="capitalize">{e.payment_status}</FrozenTd>
          </tr>
        ))}
      </tbody>
    </FrozenScrollTable>
  )
}
