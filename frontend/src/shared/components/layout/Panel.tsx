import type { ElementType, ReactNode } from 'react'

import { classNames } from '@/shared/utilities/classNames'

import styles from './Panel.module.css'

export interface PanelProps {
  children: ReactNode
  /** Adds standard internal padding. Disable when a child needs to control its own spacing (e.g. a table with a header row flush to the panel edge). */
  padded?: boolean
  /** Uses a shadow instead of a border to separate from the canvas -- reserve for content that should visually float (menus, popovers), not routine cards. */
  elevated?: boolean
  as?: ElementType
  className?: string
}

/** The base surface every card-like piece of content sits on -- a workspace section, a queue item, a future widget. */
export function Panel({ children, padded = true, elevated = false, as: Component = 'div', className }: PanelProps) {
  return (
    <Component className={classNames(styles.panel, padded && styles.padded, elevated && styles.elevated, className)}>
      {children}
    </Component>
  )
}
