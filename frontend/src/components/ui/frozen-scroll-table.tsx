import type { ReactNode } from 'react'
import { cn } from '@/lib/utils'

/**
 * Excel-style scroll surface: horizontal swipe without page overflow,
 * sticky header row + optional sticky first column.
 * Used by loans/forecast (reports uses TimeSpineTable — do not regress that).
 */
export function FrozenScrollTable({
  children,
  className,
  maxHeight,
}: {
  children: ReactNode
  className?: string
  maxHeight?: string
}) {
  return (
    <div
      className={cn(
        'rounded-md border border-border bg-card overflow-auto overscroll-contain',
        '[-webkit-overflow-scrolling:touch]',
        className,
      )}
      style={maxHeight ? { maxHeight } : undefined}
    >
      <table className="w-max min-w-full border-separate border-spacing-0 text-sm">
        {children}
      </table>
    </div>
  )
}

export function FrozenTh({
  children,
  stickyLabel,
  className,
  align = 'left',
}: {
  children?: ReactNode
  stickyLabel?: boolean
  className?: string
  align?: 'left' | 'right'
}) {
  return (
    <th
      className={cn(
        'font-medium whitespace-nowrap border-b border-border bg-muted text-foreground/90',
        'py-2 px-2.5 sticky top-0 z-20',
        align === 'left' ? 'text-left' : 'text-right',
        stickyLabel &&
          'sticky left-0 z-30 min-w-[3rem] shadow-[2px_0_0_0_hsl(var(--border))]',
        stickyLabel && 'z-40',
        className,
      )}
    >
      {children}
    </th>
  )
}

export function FrozenTd({
  children,
  stickyLabel,
  className,
  align = 'left',
}: {
  children?: ReactNode
  stickyLabel?: boolean
  className?: string
  align?: 'left' | 'right'
}) {
  return (
    <td
      className={cn(
        'whitespace-nowrap border-b border-border/50 py-2 px-2.5 tabular-nums',
        align === 'left' ? 'text-left' : 'text-right',
        stickyLabel &&
          'sticky left-0 z-10 min-w-[3rem] bg-card text-foreground shadow-[2px_0_0_0_hsl(var(--border))]',
        className,
      )}
    >
      {children}
    </td>
  )
}
