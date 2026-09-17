import { useEffect, useRef } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { sms } from '@/lib/api'
import { toast } from 'sonner'
import { Smartphone } from 'lucide-react'
import { Link } from 'react-router-dom'

/**
 * Hook to monitor SMS review queue and show toast notifications
 * when new items need review
 */
export function useSMSNotifications() {
  const queryClient = useQueryClient()
  const previousCountRef = useRef<number | null>(null)

  // Poll review queue every 30 seconds
  const { data: reviewItems } = useQuery({
    queryKey: ['sms', 'review-queue', 'pending'],
    queryFn: () => sms.reviewQueue.list({ status: 'pending' }),
    refetchInterval: 30000, // 30 seconds
    staleTime: 25000,
  })

  useEffect(() => {
    if (!reviewItems) return

    const currentCount = reviewItems.length
    const previousCount = previousCountRef.current

    // Only show notification if count increased (new items arrived)
    if (previousCount !== null && currentCount > previousCount) {
      const newItemsCount = currentCount - previousCount

      // Show toast with link to review page
      toast(
        <div className="flex items-center gap-3">
          <Smartphone className="size-5" />
          <div className="flex-1">
            <p className="font-medium">New SMS Review Items</p>
            <p className="text-sm text-muted-foreground">
              {newItemsCount} {newItemsCount === 1 ? 'item needs' : 'items need'} your attention
            </p>
          </div>
        </div>,
        {
          action: {
            label: 'Review',
            onClick: () => {
              // Navigate handled by Link component
              window.location.href = '/sms/review'
            },
          },
          duration: 10000,
        }
      )

      // Invalidate stats to refresh counts
      queryClient.invalidateQueries({ queryKey: ['sms', 'stats'] })
    }

    previousCountRef.current = currentCount
  }, [reviewItems, queryClient])

  return {
    pendingCount: reviewItems?.length || 0,
    reviewItems,
  }
}
