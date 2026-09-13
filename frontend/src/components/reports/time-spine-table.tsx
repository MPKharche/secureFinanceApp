import type { ReactNode } from 'react'
import { cn } from '@/lib/utils'

/** Excel-tight scrollable table with frozen header + first column. */
export function TimeSpineTable({
  children,
  className,
  denser = true,
}: {
  children: ReactNode
  className?: string
  denser?: boolean
}) {
  return (
    <div
      className={cn(
        'rounded-xl border border-border bg-card overflow-x-auto overscroll-x-contain',
        '[-webkit-overflow-scrolling:touch]',
        className,
      )}
    >
      <table
        className={cn(
          'w-max min-w-full border-separate border-spacing-0',
          denser ? 'text-[11px] sm:text-xs' : 'text-xs sm:text-sm',
        )}
      >
        {children}
      </table>
    </div>
  )
}

export function SpineTh({
  children,
  stickyLabel,
  className,
  align = 'right',
}: {
  children?: React.ReactNode
  stickyLabel?: boolean
  className?: string
  align?: 'left' | 'right'
}) {
  return (
    <th
      className={cn(
        'font-medium whitespace-nowrap border-b border-border bg-muted text-foreground/90',
        'py-1.5 px-2 sm:px-2.5',
        align === 'left' ? 'text-left' : 'text-right',
        stickyLabel &&
          'sticky left-0 z-30 min-w-[7.5rem] max-w-[10rem] shadow-[2px_0_0_0_hsl(var(--border))]',
        'sticky top-0 z-20',
        stickyLabel && 'z-40',
        className,
      )}
    >
      {children}
    </th>
  )
}

export function SpineTd({
  children,
  stickyLabel,
  className,
  align = 'right',
  muted,
}: {
  children?: React.ReactNode
  stickyLabel?: boolean
  className?: string
  align?: 'left' | 'right'
  muted?: boolean
}) {
  return (
    <td
      className={cn(
        'whitespace-nowrap border-b border-border/50 py-1 px-2 sm:px-2.5 tabular-nums',
        align === 'left' ? 'text-left' : 'text-right',
        stickyLabel &&
          'sticky left-0 z-10 min-w-[7.5rem] max-w-[10rem] bg-card text-foreground shadow-[2px_0_0_0_hsl(var(--border))]',
        muted && 'text-muted-foreground',
        className,
      )}
    >
      {children}
    </td>
  )
}

export function SpineLegend({ items }: { items: string[] }) {
  return (
    <div className="flex flex-wrap items-center gap-1.5 mb-2 text-[10px] sm:text-[11px] text-muted-foreground">
      {items.map((item, i) => (
        <span key={item} className="inline-flex items-center gap-1.5">
          {i > 0 && <span className="opacity-40" aria-hidden>·</span>}
          <span className="font-medium text-foreground/70">{item}</span>
        </span>
      ))}
    </div>
  )
}
