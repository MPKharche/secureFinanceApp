import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Check, X, AlertTriangle } from 'lucide-react'
import { formatCurrency } from '@/lib/format'
import { toast } from 'sonner'

interface PotentialMatch {
  schedule_entry_id: string
  transaction_id: string
  due_date: string
  transaction_date: string
  emi_amount: number
  transaction_amount: number
  confidence: string
  emi_number: number
  description: string
  account_name: string
}

interface ReviewQueueProps {
  accountId: string
  currency: string
  locale: string
}

async function fetchPendingMatches(accountId: string): Promise<PotentialMatch[]> {
  const response = await fetch(`/api/v1/loans/schedule/auto-link`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${localStorage.getItem('token')}`,
      'X-Workspace-Id': localStorage.getItem('workspace_id') || '',
    },
    body: JSON.stringify({
      account_id: accountId,
      date_tolerance_days: 7,
      amount_tolerance_percent: 5.0,
      auto_approve: false, // Don't auto-link, just return matches
    }),
  })

  if (!response.ok) throw new Error('Failed to fetch matches')
  const data = await response.json()
  
  // Filter to medium and low confidence matches only
  return (data.matches || data.potential_matches || []).filter(
    (m: PotentialMatch) => m.confidence === 'medium' || m.confidence === 'low'
  )
}

async function approveMatch(entryId: string, txId: string) {
  const response = await fetch(`/api/v1/loans/schedule/${entryId}/link`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${localStorage.getItem('token')}`,
      'X-Workspace-Id': localStorage.getItem('workspace_id') || '',
    },
    body: JSON.stringify({
      transaction_id: txId,
    }),
  })

  if (!response.ok) throw new Error('Failed to approve match')
  return response.json()
}

export function LoanReviewQueue({ accountId, currency, locale }: ReviewQueueProps) {
  const queryClient = useQueryClient()

  const { data: matches, isLoading } = useQuery({
    queryKey: ['loan-review-queue', accountId],
    queryFn: () => fetchPendingMatches(accountId),
    staleTime: 60_000,
  })

  const approveMutation = useMutation({
    mutationFn: ({ entryId, txId }: { entryId: string; txId: string }) =>
      approveMatch(entryId, txId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['loan-review-queue', accountId] })
      queryClient.invalidateQueries({ queryKey: ['loan-schedule', accountId] })
      toast.success('Match approved and linked')
    },
    onError: () => {
      toast.error('Failed to approve match')
    },
  })

  const dismissMutation = useMutation({
    mutationFn: async ({ entryId, txId }: { entryId: string; txId: string }) => {
      // TODO: Add API endpoint to dismiss matches
      // For now, just remove from UI
      return { entryId, txId }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['loan-review-queue', accountId] })
      toast.info('Match dismissed')
    },
  })

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Review Queue</CardTitle>
          <CardDescription>Loading pending matches...</CardDescription>
        </CardHeader>
      </Card>
    )
  }

  if (!matches || matches.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Review Queue</CardTitle>
          <CardDescription>No pending matches to review</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8 text-muted-foreground">
            <Check className="w-12 h-12 mx-auto mb-2 text-emerald-500" />
            <p>All transactions are linked or have high confidence matches!</p>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Review Queue</CardTitle>
        <CardDescription>
          {matches.length} pending match{matches.length !== 1 ? 'es' : ''} need review
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {matches.map((match) => {
          const dateDiff = Math.abs(
            (new Date(match.transaction_date).getTime() - new Date(match.due_date).getTime()) /
              (1000 * 60 * 60 * 24)
          )
          const amountDiff = Math.abs(match.emi_amount - Math.abs(match.transaction_amount))
          const amountDiffPct = (amountDiff / match.emi_amount) * 100

          return (
            <div
              key={`${match.schedule_entry_id}-${match.transaction_id}`}
              className="flex items-start gap-3 p-4 border rounded-lg bg-muted/30"
            >
              <AlertTriangle className="w-5 h-5 text-amber-500 shrink-0 mt-0.5" />
              
              <div className="flex-1 min-w-0 space-y-2">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <div className="font-medium text-foreground">
                      EMI #{match.emi_number} • {match.due_date}
                    </div>
                    <div className="text-sm text-muted-foreground mt-0.5">
                      {match.description}
                    </div>
                  </div>
                  <Badge
                    variant={match.confidence === 'medium' ? 'default' : 'secondary'}
                    className="shrink-0"
                  >
                    {match.confidence}
                  </Badge>
                </div>

                <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm">
                  <div className="text-muted-foreground">Expected:</div>
                  <div className="font-semibold tabular-nums">
                    {formatCurrency(match.emi_amount, currency, locale)}
                  </div>
                  
                  <div className="text-muted-foreground">Transaction:</div>
                  <div className="font-semibold tabular-nums">
                    {formatCurrency(Math.abs(match.transaction_amount), currency, locale)}
                  </div>
                  
                  <div className="text-muted-foreground">Date diff:</div>
                  <div className={dateDiff > 3 ? 'text-amber-600' : ''}>
                    {dateDiff === 0 ? 'Same day' : `${Math.round(dateDiff)} day${dateDiff !== 1 ? 's' : ''}`}
                  </div>
                  
                  {amountDiffPct > 1 && (
                    <>
                      <div className="text-muted-foreground">Amount diff:</div>
                      <div className="text-amber-600">
                        {formatCurrency(amountDiff, currency, locale)} ({amountDiffPct.toFixed(1)}%)
                      </div>
                    </>
                  )}
                </div>
              </div>

              <div className="flex flex-col gap-2 shrink-0">
                <Button
                  size="sm"
                  onClick={() =>
                    approveMutation.mutate({
                      entryId: match.schedule_entry_id,
                      txId: match.transaction_id,
                    })
                  }
                  disabled={approveMutation.isPending}
                  className="h-8"
                >
                  <Check className="w-4 h-4 mr-1" />
                  Approve
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() =>
                    dismissMutation.mutate({
                      entryId: match.schedule_entry_id,
                      txId: match.transaction_id,
                    })
                  }
                  disabled={dismissMutation.isPending}
                  className="h-8"
                >
                  <X className="w-4 h-4 mr-1" />
                  Dismiss
                </Button>
              </div>
            </div>
          )
        })}
      </CardContent>
    </Card>
  )
}
