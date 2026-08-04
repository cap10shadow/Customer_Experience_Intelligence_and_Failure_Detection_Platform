import type { ElementType, ReactNode } from 'react'

import type { SpaceScale } from '@/shared/types/spacing'
import { spaceVar } from '@/shared/types/spacing'
import { classNames } from '@/shared/utilities/classNames'

export interface GridProps {
  children: ReactNode
  /** Minimum column width before wrapping to the next row -- the grid reflows itself, no breakpoint-specific column counts to maintain. */
  minColumnWidth?: number
  gap?: SpaceScale
  as?: ElementType
  className?: string
}

/**
 * A responsive, auto-flowing grid built on `repeat(auto-fit, minmax(...))`.
 * Future dashboard widgets (Home's Operational Analytics section, Action
 * Center's queue cards, etc.) drop into this without any
 * breakpoint-specific column configuration -- it is the architectural
 * reason "future dashboard widgets should naturally adapt without
 * requiring redesign."
 */
export function Grid({ children, minColumnWidth = 280, gap = 6, as: Component = 'div', className }: GridProps) {
  return (
    <Component
      className={classNames(className)}
      style={{
        display: 'grid',
        gridTemplateColumns: `repeat(auto-fit, minmax(min(${minColumnWidth}px, 100%), 1fr))`,
        gap: spaceVar(gap),
      }}
    >
      {children}
    </Component>
  )
}
