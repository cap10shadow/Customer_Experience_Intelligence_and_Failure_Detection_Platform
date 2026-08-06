import type { ReactNode } from 'react'

import { InvestigationNavigator } from './InvestigationNavigator'
import styles from './InvestigationLayout.module.css'

export interface InvestigationLayoutProps {
  children: ReactNode
}

/**
 * Composes the persistent `InvestigationNavigator` alongside the
 * reading column. Desktop/laptop show them side by side, with the
 * navigator sticky so it stays visible while reading; below the 1024px
 * threshold already used for the app's own sidebar (see
 * `Sidebar.module.css`), the navigator moves above the content as a
 * horizontal section-jump bar. Purely a CSS media-query switch -- no
 * JS breakpoint state, since nothing here is interactive the way the
 * Sidebar's collapse toggle is; it's a layout reflow, not a persisted
 * preference. Narrative order never changes; only this wrapping layout
 * adapts.
 */
export function InvestigationLayout({ children }: InvestigationLayoutProps) {
  return (
    <div className={styles.layout}>
      <div className={styles.navigatorColumn}>
        <InvestigationNavigator />
      </div>
      <div className={styles.contentColumn}>{children}</div>
    </div>
  )
}
