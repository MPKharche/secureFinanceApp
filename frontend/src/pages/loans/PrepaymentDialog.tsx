import { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import {
  Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { localDateString } from '@/lib/date-utils'

interface Props {
  accountId: string
  open: boolean
  onOpenChange: (open: boolean) => void
  onSuccess?: () => void
  /** NRP / commercial — do not force 0% penalty */
  isNrpOrCommercial?: boolean
}

export function PrepaymentDialog({
  accountId,
  open,
  onOpenChange,
  onSuccess,
  isNrpOrCommercial = false,
}: Props) {
  const [amount, setAmount] = useState('')
  // Keep EMI (cut tenure) is the one-tap default — banks often auto-cut EMI
  const [method, setMethod] = useState<'reduce_tenure' | 'reduce_emi'>('reduce_tenure')
  const [penaltyRate, setPenaltyRate] = useState(isNrpOrCommercial ? '2' : '0')
  const [penaltyBasis, setPenaltyBasis] = useState<'outstanding' | 'prepayment_amount'>('outstanding')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (open) {
      setPenaltyRate(isNrpOrCommercial ? '2' : '0')
    }
  }, [open, isNrpOrCommercial])

  async function submit() {
    setBusy(true)
    setError(null)
    try {
      const response = await fetch('/api/v1/loans/prepayments', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('token')}`,
          'X-Workspace-Id': localStorage.getItem('workspace_id') || '',
        },
        body: JSON.stringify({
          account_id: accountId,
          prepayment_amount: amount,
          prepayment_date: localDateString(new Date()),
          recalculation_method: method,
          penalty_rate: parseFloat(penaltyRate || '0'),
          penalty_basis: penaltyBasis,
        }),
      })
      if (!response.ok) throw new Error(await response.text())
      onOpenChange(false)
      onSuccess?.()
    } catch (e: any) {
      setError(e?.message || 'Prepayment failed')
    } finally {
      setBusy(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Make prepayment</DialogTitle>
        </DialogHeader>
        <div className="space-y-3">
          <div>
            <Label>Amount</Label>
            <Input type="number" value={amount} onChange={(e) => setAmount(e.target.value)} />
          </div>
          <div>
            <Label>After prepay</Label>
            <div className="flex gap-2 mt-1">
              <Button
                type="button"
                size="sm"
                variant={method === 'reduce_tenure' ? 'default' : 'outline'}
                className="flex-1"
                onClick={() => setMethod('reduce_tenure')}
              >
                Keep EMI
              </Button>
              <Button
                type="button"
                size="sm"
                variant={method === 'reduce_emi' ? 'default' : 'outline'}
                className="flex-1"
                onClick={() => setMethod('reduce_emi')}
              >
                Cut EMI
              </Button>
            </div>
            <p className="text-[11px] text-muted-foreground mt-1">
              Banks often auto-cut EMI — Keep EMI shortens tenure instead.
            </p>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <div>
              <Label>Penalty %</Label>
              <Input
                type="number"
                step="0.1"
                value={penaltyRate}
                onChange={(e) => setPenaltyRate(e.target.value)}
              />
            </div>
            <div>
              <Label>Basis</Label>
              <select
                className="w-full border border-border rounded-md h-9 px-2 bg-background text-sm"
                value={penaltyBasis}
                onChange={(e) =>
                  setPenaltyBasis(e.target.value as 'outstanding' | 'prepayment_amount')
                }
              >
                <option value="outstanding">Of outstanding</option>
                <option value="prepayment_amount">Of prepay amt</option>
              </select>
            </div>
          </div>
          {isNrpOrCommercial && (
            <p className="text-[11px] text-amber-700 dark:text-amber-300">
              Commercial / NRP — penalty may apply; not forced to zero.
            </p>
          )}
          {error && <p className="text-sm text-destructive">{error}</p>}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button disabled={busy || !amount} onClick={submit}>
            {busy ? 'Saving…' : 'Apply'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
