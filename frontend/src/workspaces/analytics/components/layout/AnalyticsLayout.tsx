import type { ReactNode } from 'react'

import { AnalyticsNavigator } from './AnalyticsNavigator'
import styles from './AnalyticsLayout.module.css'

export interface AnalyticsLayoutProps {
  children: ReactNode
}

/**
 * Composes the persistent `AnalyticsNavigator` alongside the reading
 * column -- the same pure-CSS 1024px switch as `InvestigationLayout`
 * and `RecommendationLayout` (desktop/laptop side by side, tablet/mobile
 * stacked, navigator above content). Narrative order never changes;
 * only this wrapping layout adapts.
 */
export function AnalyticsLayout({ children }: AnalyticsLayoutProps) {
  return (
    <div className={styles.layout}>
      <div className={styles.navigatorColumn}>
        <AnalyticsNavigator />
      </div>
      <div className={styles.contentColumn}>{children}</div>
    </div>
  )
}
