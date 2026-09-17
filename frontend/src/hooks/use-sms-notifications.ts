import { useEffect, useRef } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { sms } from '@/lib/api'
import { toast } from 'sonner'

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
      toast.success(
        `${newItemsCount} new SMS ${newItemsCount === 1 ? 'item needs' : 'items need'} your attention`,
        {
          action: {
            label: 'Review',
            onClick: () => {
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
