import type { ReactNode } from 'react'

import { classNames } from '@/shared/utilities/classNames'

export interface NavigationGroupProps {
  /** Accessible name for this group of links -- not necessarily visible (see SidebarSection for a visible heading). */
  label: string
  children: ReactNode
  className?: string
}

/**
 * A semantic list of navigation entries. Only one group exists today
 * (the primary workspace list) -- this exists as the extension point a
 * future secondary grouping (e.g. "Pinned") plugs into without changing
 * how Sidebar or NavigationItem work.
 */
export function NavigationGroup({ label, children, className }: NavigationGroupProps) {
  return (
    <ul aria-label={label} className={classNames(className)} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-1)' }}>
      {children}
    </ul>
  )
}
