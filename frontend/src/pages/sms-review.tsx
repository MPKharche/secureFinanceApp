import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { sms } from '@/lib/api'
import { categories as categoriesApi } from '@/lib/api'
import { toast } from 'sonner'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import { extractApiError } from '@/lib/api-errors'
import { CheckCircle2, XCircle, AlertCircle, Merge, HelpCircle, Smartphone } from 'lucide-react'
import { format } from 'date-fns'
import type { SMSReviewQueueItem, Category } from '@/types'

type ReviewType = 'all' | 'duplicate' | 'uncategorized' | 'failed_parse' | 'low_confidence'

export default function SMSReviewPage() {
  const [reviewTypeFilter, setReviewTypeFilter] = useState<ReviewType>('all')
  const queryClient = useQueryClient()

  // Fetch review queue
  const { data: reviewItems, isLoading } = useQuery({
    queryKey: ['sms', 'review-queue', reviewTypeFilter],
    queryFn: async () => {
      const params = reviewTypeFilter !== 'all' ? { review_type: reviewTypeFilter, status: 'pending' as const } : { status: 'pending' as const }
      return sms.reviewQueue.list(params)
    },
    refetchInterval: 30000, // Poll every 30 seconds for new items
  })

  // Fetch categories for uncategorized items
  const { data: categories } = useQuery({
    queryKey: ['categories'],
    queryFn: categoriesApi.list,
  })

  // Mutations
  const approveMutation = useMutation({
    mutationFn: ({ reviewId, notes }: { reviewId: string; notes?: string }) =>
      sms.reviewQueue.approve(reviewId, { resolution_notes: notes }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sms', 'review-queue'] })
      toast.success('Item approved successfully')
    },
    onError: (error) => {
      toast.error(`Failed to approve: ${extractApiError(error)}`)
    },
  })

  const rejectMutation = useMutation({
    mutationFn: ({ reviewId, notes }: { reviewId: string; notes?: string }) =>
      sms.reviewQueue.reject(reviewId, { resolution_notes: notes }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sms', 'review-queue'] })
      toast.success('Item rejected successfully')
    },
    onError: (error) => {
      toast.error(`Failed to reject: ${extractApiError(error)}`)
    },
  })

  const approveUncategorizedMutation = useMutation({
    mutationFn: ({ reviewId, categoryId }: { reviewId: string; categoryId: string }) =>
      sms.reviewQueue.approveUncategorized(reviewId, { category_id: categoryId }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sms', 'review-queue'] })
      toast.success('Merchant categorized successfully')
    },
    onError: (error) => {
      toast.error(`Failed to categorize: ${extractApiError(error)}`)
    },
  })

  const mergeMutation = useMutation({
    mutationFn: ({ reviewId, keepTransactionId }: { reviewId: string; keepTransactionId: string }) =>
      sms.reviewQueue.merge(reviewId, { keep_transaction_id: keepTransactionId }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sms', 'review-queue'] })
      toast.success('Duplicate merged successfully')
    },
    onError: (error) => {
      toast.error(`Failed to merge: ${extractApiError(error)}`)
    },
  })

  const pendingCount = reviewItems?.length || 0

  return (
    <div className="space-y-6 pb-16">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-foreground tracking-tight flex items-center gap-2 mb-2">
          <Smartphone className="size-6" />
          SMS Review Queue
        </h1>
        <p className="text-sm text-muted-foreground">
          {pendingCount} item{pendingCount !== 1 ? 's' : ''} need{pendingCount === 1 ? 's' : ''} your attention
        </p>
      </div>

      {/* Filter */}
      <div className="flex items-center gap-4">
        <Select value={reviewTypeFilter} onValueChange={(value) => setReviewTypeFilter(value as ReviewType)}>
          <SelectTrigger className="w-[200px]">
            <SelectValue placeholder="Filter by type" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Items</SelectItem>
            <SelectItem value="duplicate">Duplicates</SelectItem>
            <SelectItem value="uncategorized">Uncategorized</SelectItem>
            <SelectItem value="failed_parse">Failed Parse</SelectItem>
            <SelectItem value="low_confidence">Low Confidence</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Review Items */}
      {isLoading ? (
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-48" />
          ))}
        </div>
      ) : !reviewItems || reviewItems.length === 0 ? (
        <Card>
          <CardContent className="py-12">
            <div className="flex flex-col items-center justify-center text-center">
              <CheckCircle2 className="size-12 text-green-500 mb-4" />
              <h3 className="text-lg font-semibold mb-2">All caught up!</h3>
              <p className="text-muted-foreground">No items need review right now.</p>
            </div>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {reviewItems.map((item) => (
            <ReviewCard
              key={item.id}
              item={item}
              categories={categories || []}
              onApprove={(notes) => approveMutation.mutate({ reviewId: item.id, notes })}
              onReject={(notes) => rejectMutation.mutate({ reviewId: item.id, notes })}
              onCategorize={(categoryId) => approveUncategorizedMutation.mutate({ reviewId: item.id, categoryId })}
              onMerge={(keepTransactionId) => mergeMutation.mutate({ reviewId: item.id, keepTransactionId })}
              isProcessing={
                approveMutation.isPending ||
                rejectMutation.isPending ||
                approveUncategorizedMutation.isPending ||
                mergeMutation.isPending
              }
            />
          ))}
        </div>
      )}
    </div>
  )
}

interface ReviewCardProps {
  item: SMSReviewQueueItem
  categories: Category[]
  onApprove: (notes?: string) => void
  onReject: (notes?: string) => void
  onCategorize: (categoryId: string) => void
  onMerge: (keepTransactionId: string) => void
  isProcessing: boolean
}

function ReviewCard({ item, categories, onApprove, onReject, onCategorize, onMerge, isProcessing }: ReviewCardProps) {
  const [selectedCategory, setSelectedCategory] = useState<string>('')
  const [selectedTransaction, setSelectedTransaction] = useState<string>('')

  const typeConfig = {
    duplicate: {
      icon: <Merge className="size-5" />,
      color: 'bg-amber-500/10 text-amber-600 dark:text-amber-400',
      label: 'Duplicate',
    },
    uncategorized: {
      icon: <HelpCircle className="size-5" />,
      color: 'bg-blue-500/10 text-blue-600 dark:text-blue-400',
      label: 'Uncategorized',
    },
    failed_parse: {
      icon: <XCircle className="size-5" />,
      color: 'bg-red-500/10 text-red-600 dark:text-red-400',
      label: 'Parse Failed',
    },
    low_confidence: {
      icon: <AlertCircle className="size-5" />,
      color: 'bg-orange-500/10 text-orange-600 dark:text-orange-400',
      label: 'Low Confidence',
    },
  }

  const config = typeConfig[item.review_type]

  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <div className={`p-1.5 rounded-md ${config.color}`}>{config.icon}</div>
              <CardTitle className="text-lg">{config.label}</CardTitle>
              <Badge variant="outline" className="text-xs">
                {item.sender || 'Unknown'}
              </Badge>
            </div>
            <CardDescription className="text-xs">
              {format(new Date(item.created_at), 'MMM dd, yyyy HH:mm')}
            </CardDescription>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* SMS Body */}
        <div className="bg-muted/50 rounded-md p-3">
          <p className="text-sm font-mono whitespace-pre-wrap">{item.body || 'No SMS body available'}</p>
        </div>

        {/* Parsed Data */}
        {item.parsed_data && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
            {item.parsed_data.merchant && (
              <div>
                <span className="text-muted-foreground block text-xs mb-1">Merchant</span>
                <span className="font-medium">{item.parsed_data.merchant}</span>
              </div>
            )}
            {item.parsed_data.amount !== undefined && (
              <div>
                <span className="text-muted-foreground block text-xs mb-1">Amount</span>
                <span className="font-medium">₹{item.parsed_data.amount.toFixed(2)}</span>
              </div>
            )}
            {item.parsed_data.transaction_type && (
              <div>
                <span className="text-muted-foreground block text-xs mb-1">Type</span>
                <Badge variant={item.parsed_data.transaction_type === 'debit' ? 'destructive' : 'default'}>
                  {item.parsed_data.transaction_type}
                </Badge>
              </div>
            )}
            {item.parsed_data.confidence !== undefined && (
              <div>
                <span className="text-muted-foreground block text-xs mb-1">Confidence</span>
                <span className="font-medium">{(item.parsed_data.confidence * 100).toFixed(0)}%</span>
              </div>
            )}
          </div>
        )}

        {/* Type-specific content */}
        {item.review_type === 'duplicate' && item.review_data.duplicate_matches && (
          <div className="space-y-2">
            <h4 className="text-sm font-medium">Possible Duplicates:</h4>
            <div className="space-y-2">
              {item.review_data.duplicate_matches.map((match) => (
                <label
                  key={match.transaction_id}
                  className={`flex items-center gap-3 p-3 rounded-md border cursor-pointer transition-colors ${
                    selectedTransaction === match.transaction_id
                      ? 'border-primary bg-primary/5'
                      : 'border-border hover:border-primary/50'
                  }`}
                >
                  <input
                    type="radio"
                    name={`duplicate-${item.id}`}
                    value={match.transaction_id}
                    checked={selectedTransaction === match.transaction_id}
                    onChange={() => setSelectedTransaction(match.transaction_id)}
                    className="size-4"
                  />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 text-sm">
                      <span className="font-medium truncate">{match.description}</span>
                      <Badge variant="outline" className="text-xs">
                        ₹{match.amount}
                      </Badge>
                    </div>
                    <div className="text-xs text-muted-foreground">
                      {format(new Date(match.date), 'MMM dd, yyyy')}
                      {match.account_name && ` • ${match.account_name}`}
                    </div>
                  </div>
                </label>
              ))}
            </div>
          </div>
        )}

        {item.review_type === 'uncategorized' && (
          <div className="space-y-2">
            <label className="text-sm font-medium">Select Category:</label>
            <Select value={selectedCategory} onValueChange={setSelectedCategory}>
              <SelectTrigger>
                <SelectValue placeholder="Choose a category..." />
              </SelectTrigger>
              <SelectContent>
                {categories.map((cat) => (
                  <SelectItem key={cat.id} value={cat.id}>
                    {cat.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {item.review_data.merchant && (
              <p className="text-xs text-muted-foreground">
                Future transactions from "{item.review_data.merchant}" will be automatically categorized.
              </p>
            )}
          </div>
        )}

        {item.review_type === 'failed_parse' && item.review_data.parse_error && (
          <Alert variant="destructive">
            <AlertCircle className="size-4" />
            <AlertTitle>Parse Error</AlertTitle>
            <AlertDescription className="text-xs">{item.review_data.parse_error}</AlertDescription>
          </Alert>
        )}

        {item.review_type === 'low_confidence' && (
          <Alert variant="warning">
            <AlertCircle className="size-4" />
            <AlertTitle>Low Confidence Parse</AlertTitle>
            <AlertDescription className="text-xs">
              The SMS parser was unable to extract transaction details with high confidence. Please review the parsed
              data above.
            </AlertDescription>
          </Alert>
        )}

        {/* Actions */}
        <div className="flex items-center gap-2 pt-2">
          {item.review_type === 'duplicate' ? (
            <>
              <Button
                size="sm"
                onClick={() => selectedTransaction && onMerge(selectedTransaction)}
                disabled={!selectedTransaction || isProcessing}
              >
                <Merge className="size-4" />
                Merge with Selected
              </Button>
              <Button size="sm" variant="outline" onClick={() => onReject()} disabled={isProcessing}>
                <XCircle className="size-4" />
                Not a Duplicate
              </Button>
            </>
          ) : item.review_type === 'uncategorized' ? (
            <>
              <Button
                size="sm"
                onClick={() => selectedCategory && onCategorize(selectedCategory)}
                disabled={!selectedCategory || isProcessing}
              >
                <CheckCircle2 className="size-4" />
                Categorize
              </Button>
              <Button size="sm" variant="outline" onClick={() => onReject()} disabled={isProcessing}>
                <XCircle className="size-4" />
                Skip
              </Button>
            </>
          ) : (
            <>
              <Button size="sm" onClick={() => onApprove()} disabled={isProcessing}>
                <CheckCircle2 className="size-4" />
                Approve
              </Button>
              <Button size="sm" variant="outline" onClick={() => onReject()} disabled={isProcessing}>
                <XCircle className="size-4" />
                Reject
              </Button>
            </>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
