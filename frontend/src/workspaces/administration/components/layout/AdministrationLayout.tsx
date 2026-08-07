import type { ReactNode } from 'react'

import { AdministrationNavigator } from './AdministrationNavigator'
import styles from './AdministrationLayout.module.css'

export interface AdministrationLayoutProps {
  children: ReactNode
}

/**
 * Composes the persistent `AdministrationNavigator` alongside the
 * single-column reading content -- the same pure-CSS 1024px switch as
 * `InvestigationLayout`, `RecommendationLayout`, and `AnalyticsLayout`
 * (desktop/laptop side by side, tablet/mobile stacked, navigator above
 * content). Section order never changes; only this wrapping layout
 * adapts.
 */
export function AdministrationLayout({ children }: AdministrationLayoutProps) {
  return (
    <div className={styles.layout}>
      <div className={styles.navigatorColumn}>
        <AdministrationNavigator />
      </div>
      <div className={styles.contentColumn}>{children}</div>
    </div>
  )
}
