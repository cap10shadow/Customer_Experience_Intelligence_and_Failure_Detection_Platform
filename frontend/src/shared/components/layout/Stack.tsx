import type { CSSProperties, ElementType, ReactNode } from 'react'

import type { SpaceScale } from '@/shared/types/spacing'
import { spaceVar } from '@/shared/types/spacing'
import { classNames } from '@/shared/utilities/classNames'

export interface StackProps {
  children: ReactNode
  /** 'column' (default) stacks vertically; 'row' arranges horizontally. */
  direction?: 'row' | 'column'
  gap?: SpaceScale
  align?: CSSProperties['alignItems']
  justify?: CSSProperties['justifyContent']
  wrap?: boolean
  as?: ElementType
  className?: string
}

/** The base flex-layout primitive every foundation component composes with instead of hand-rolling flexbox. */
export function Stack({
  children,
  direction = 'column',
  gap = 0,
  align,
  justify,
  wrap = false,
  as: Component = 'div',
  className,
}: StackProps) {
  return (
    <Component
      className={classNames(className)}
      style={{
        display: 'flex',
        flexDirection: direction,
        gap: spaceVar(gap),
        alignItems: align,
        justifyContent: justify,
        flexWrap: wrap ? 'wrap' : 'nowrap',
      }}
    >
      {children}
    </Component>
  )
}
