import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { useState } from 'react'
import { formatCurrency } from '@/lib/format'
import {
  FrozenScrollTable,
  FrozenTd,
  FrozenTh,
} from '@/components/ui/frozen-scroll-table'
import { LinkTransactionDialog } from '@/components/loans/LinkTransactionDialog'
import { toast } from 'sonner'

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
  principal_percentage?: number
  linked_transaction_ids?: string
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
  const navigate = useNavigate()
  const [linkDialogOpen, setLinkDialogOpen] = useState(false)
  const [selectedEntry, setSelectedEntry] = useState<Entry | null>(null)
  
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['loan-schedule', accountId],
    queryFn: () => fetchSchedule(accountId),
  })
  
  const navigateToTransactions = (txIds: string) => {
    const ids = txIds.split(',').map(id => id.trim())
    if (ids.length === 1) {
      navigate(`/transactions?highlight=${ids[0]}`)
    } else {
      // Multiple transactions: show all
      navigate(`/transactions?q=${ids.join(' ')}`)
    }
  }
  
  const handleLinkTransactions = async (entryId: string, txIds: string[]) => {
    try {
      const response = await fetch(`/api/v1/loans/schedule/${entryId}/link`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('token')}`,
          'X-Workspace-Id': localStorage.getItem('workspace_id') || '',
        },
        body: JSON.stringify({
          transaction_ids: txIds.join(','),
        }),
      })
      
      if (!response.ok) throw new Error('Failed to link transactions')
      
      toast.success(`Linked ${txIds.length} transaction${txIds.length > 1 ? 's' : ''} to EMI`)
      refetch()
    } catch (error) {
      toast.error('Failed to link transactions')
      throw error
    }
  }
  
  const handleStatusClick = (e: Entry) => {
    if (e.payment_status === 'paid' && e.linked_transaction_ids) {
      navigateToTransactions(e.linked_transaction_ids)
    } else if (e.payment_status === 'scheduled') {
      setSelectedEntry(e)
      setLinkDialogOpen(true)
    }
  }
  
  if (isLoading) return <div className="py-8 text-center text-muted-foreground">Loading schedule…</div>
  if (error) return <div className="py-8 text-center text-destructive">Failed to load schedule</div>
  if (!data?.length) return <div className="py-8 text-center text-muted-foreground">No schedule entries</div>
  
  return (
    <>
      <FrozenScrollTable maxHeight="70vh" className="rounded-md">
        <thead>
          <tr>
            <FrozenTh stickyLabel>#</FrozenTh>
            <FrozenTh>Due</FrozenTh>
            <FrozenTh align="right">Principal</FrozenTh>
            <FrozenTh align="right">Interest</FrozenTh>
            <FrozenTh align="right">EMI</FrozenTh>
            <FrozenTh align="right">Principal %</FrozenTh>
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
                <div className="relative h-8 flex items-center justify-end">
                  {/* Background dual-color bar */}
                  <div className="absolute inset-0 flex rounded overflow-hidden">
                    <div 
                      className="bg-emerald-500/20 border-r border-emerald-600/30"
                      style={{ width: `${e.principal_percentage || 0}%` }}
                    />
                    <div 
                      className="bg-rose-500/20"
                      style={{ width: `${100 - (e.principal_percentage || 0)}%` }}
                    />
                  </div>
                  {/* Percentage text */}
                  <span className="relative z-10 text-sm font-semibold px-2 text-foreground">
                    {e.principal_percentage?.toFixed(1) || '0.0'}%
                  </span>
                </div>
              </FrozenTd>
              <FrozenTd align="right">
                {formatCurrency(Number(e.closing_balance), currency, locale)}
              </FrozenTd>
              <FrozenTd className="capitalize">
                {e.payment_status === 'paid' && e.linked_transaction_ids ? (
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => navigateToTransactions(e.linked_transaction_ids!)}
                      className="text-emerald-600 hover:text-emerald-700 hover:underline font-medium inline-flex items-center gap-1"
                      title="View linked transaction(s)"
                    >
                      Paid
                      <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                      </svg>
                    </button>
                    {e.linked_transaction_ids.split(',').length > 1 && (
                      <span className="text-[10px] bg-blue-50 text-blue-700 dark:bg-blue-950/40 dark:text-blue-300 border border-blue-200 dark:border-blue-900 px-1.5 py-0.5 rounded-full" title="Multiple transactions">
                        {e.linked_transaction_ids.split(',').length} txs
                      </span>
                    )}
                  </div>
                ) : e.payment_status === 'partial' ? (
                  <div className="flex items-center gap-1">
                    <span className="text-amber-600 dark:text-amber-400 font-medium">Partial</span>
                    <svg className="w-3 h-3 text-amber-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                    </svg>
                  </div>
                ) : e.payment_status === 'scheduled' ? (
                  <button
                    onClick={() => handleStatusClick(e)}
                    className="text-muted-foreground hover:text-primary hover:underline inline-flex items-center gap-1"
                    title="Link to transaction(s)"
                  >
                    Scheduled
                    <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
                    </svg>
                  </button>
                ) : e.payment_status === 'missed' ? (
                  <span className="text-rose-600 dark:text-rose-400 font-medium">Missed</span>
                ) : (
                  <span className={e.payment_status === 'paid' ? 'text-emerald-600 font-medium' : ''}>
                    {e.payment_status}
                  </span>
                )}
              </FrozenTd>
            </tr>
          ))}
        </tbody>
      </FrozenScrollTable>
      
      <LinkTransactionDialog
        open={linkDialogOpen}
        onClose={() => {
          setLinkDialogOpen(false)
          setSelectedEntry(null)
        }}
        scheduleEntry={selectedEntry}
        accountId={accountId}
        currency={currency}
        locale={locale}
        onLink={handleLinkTransactions}
      />
    </>
  )
}
