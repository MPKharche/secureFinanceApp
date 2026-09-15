import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { AlertTriangle } from 'lucide-react'
import { formatCurrency } from '@/lib/format'

interface Transaction {
  id: string
  date: string
  description: string
  amount: number
  currency: string
  account_id: string
}

interface Entry {
  id: string
  emi_number: number
  due_date: string
  emi_amount: number
  payment_status: string
  account_id: string
}

interface LinkTransactionDialogProps {
  open: boolean
  onClose: () => void
  scheduleEntry: Entry | null
  accountId: string
  currency: string
  locale: string
  onLink: (entryId: string, txIds: string[]) => Promise<void>
}

async function fetchCandidateTransactions(
  scheduleEntry: Entry | null,
  accountId: string
): Promise<Transaction[]> {
  if (!scheduleEntry) return []

  const dueDate = new Date(scheduleEntry.due_date)
  const fromDate = new Date(dueDate)
  fromDate.setDate(fromDate.getDate() - 7)
  const toDate = new Date(dueDate)
  toDate.setDate(toDate.getDate() + 7)

  const minAmount = scheduleEntry.emi_amount * 0.8
  const maxAmount = scheduleEntry.emi_amount * 1.2

  const params = new URLSearchParams({
    account_id: accountId,
    from: fromDate.toISOString().split('T')[0],
    to: toDate.toISOString().split('T')[0],
    min_amount: minAmount.toString(),
    max_amount: maxAmount.toString(),
    type: 'debit',
    limit: '50',
  })

  const response = await fetch(`/api/v1/transactions?${params}`, {
    headers: {
      Authorization: `Bearer ${localStorage.getItem('token')}`,
      'X-Workspace-Id': localStorage.getItem('workspace_id') || '',
    },
  })

  if (!response.ok) throw new Error('Failed to fetch transactions')
  const data = await response.json()
  return data.items || []
}

export function LinkTransactionDialog({
  open,
  onClose,
  scheduleEntry,
  accountId,
  currency,
  locale,
  onLink,
}: LinkTransactionDialogProps) {
  const [selectedTxIds, setSelectedTxIds] = useState<string[]>([])
  const [isLinking, setIsLinking] = useState(false)

  const { data: candidates, isLoading } = useQuery({
    queryKey: ['tx-candidates', scheduleEntry?.id],
    queryFn: () => fetchCandidateTransactions(scheduleEntry, accountId),
    enabled: open && !!scheduleEntry,
  })

  const totalSelected =
    candidates
      ?.filter((tx) => selectedTxIds.includes(tx.id))
      .reduce((sum, tx) => sum + Math.abs(tx.amount), 0) || 0

  const emiAmount = scheduleEntry?.emi_amount || 0
  const isExactMatch = Math.abs(totalSelected - emiAmount) < 1
  const isOverpaid = totalSelected > emiAmount + 1
  const isPartial = totalSelected > 0 && totalSelected < emiAmount - 1

  const handleLink = async () => {
    if (!scheduleEntry || selectedTxIds.length === 0) return
    setIsLinking(true)
    try {
      await onLink(scheduleEntry.id, selectedTxIds)
      setSelectedTxIds([])
      onClose()
    } finally {
      setIsLinking(false)
    }
  }

  const handleToggle = (txId: string) => {
    setSelectedTxIds((prev) =>
      prev.includes(txId) ? prev.filter((id) => id !== txId) : [...prev, txId]
    )
  }

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl max-h-[80vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>Link Transactions to EMI #{scheduleEntry?.emi_number}</DialogTitle>
          <DialogDescription>
            Due: {scheduleEntry?.due_date} • EMI:{' '}
            {formatCurrency(emiAmount, currency, locale)}
          </DialogDescription>
        </DialogHeader>

        <div className="flex-1 overflow-y-auto space-y-2 pr-2">
          {isLoading ? (
            <div className="py-8 text-center text-muted-foreground">
              Loading candidate transactions...
            </div>
          ) : !candidates || candidates.length === 0 ? (
            <div className="py-8 text-center text-muted-foreground">
              No matching transactions found within ±7 days
            </div>
          ) : (
            candidates.map((tx) => {
              const isSelected = selectedTxIds.includes(tx.id)
              const dateDiff = Math.abs(
                (new Date(tx.date).getTime() - new Date(scheduleEntry?.due_date || '').getTime()) /
                  (1000 * 60 * 60 * 24)
              )
              const amountMatch = Math.abs(Math.abs(tx.amount) - emiAmount) / emiAmount < 0.02

              return (
                <label
                  key={tx.id}
                  className={`flex items-center gap-3 p-3 border rounded-lg cursor-pointer transition-colors ${
                    isSelected
                      ? 'bg-primary/5 border-primary/30'
                      : 'hover:bg-muted/50 border-border'
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={isSelected}
                    onChange={() => handleToggle(tx.id)}
                    className="h-4 w-4 rounded border-border accent-primary cursor-pointer"
                  />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <div className="font-medium text-foreground truncate">{tx.description}</div>
                      {amountMatch && (
                        <span className="shrink-0 text-xs bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border border-emerald-500/20 px-1.5 py-0.5 rounded">
                          Exact
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-3 text-sm text-muted-foreground mt-0.5">
                      <span>{tx.date}</span>
                      <span>•</span>
                      <span className="font-semibold tabular-nums">
                        {formatCurrency(Math.abs(tx.amount), currency, locale)}
                      </span>
                      {dateDiff <= 1 && (
                        <>
                          <span>•</span>
                          <span className="text-emerald-600 dark:text-emerald-400">
                            {dateDiff === 0 ? 'Same day' : '1 day diff'}
                          </span>
                        </>
                      )}
                    </div>
                  </div>
                </label>
              )
            })
          )}
        </div>

        <div className="flex flex-col gap-3 pt-4 border-t">
          <div className="flex items-center justify-between">
            <div className="text-sm">
              <span className="text-muted-foreground">Selected total:</span>
              <span className="ml-2 font-semibold tabular-nums text-foreground">
                {formatCurrency(totalSelected, currency, locale)}
              </span>
            </div>
            {!isExactMatch && totalSelected > 0 && (
              <div className="flex items-center gap-1.5 text-sm">
                <AlertTriangle size={14} className="text-amber-500" />
                <span className="text-amber-600 dark:text-amber-400 font-medium">
                  {isOverpaid && 'Overpaid'}
                  {isPartial && `Partial (${Math.round((totalSelected / emiAmount) * 100)}%)`}
                </span>
              </div>
            )}
          </div>

          <div className="flex gap-2">
            <Button variant="outline" onClick={onClose} className="flex-1">
              Cancel
            </Button>
            <Button
              onClick={handleLink}
              disabled={selectedTxIds.length === 0 || isLinking}
              className="flex-1"
            >
              {isLinking
                ? 'Linking...'
                : `Link ${selectedTxIds.length} Transaction${selectedTxIds.length !== 1 ? 's' : ''}`}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
