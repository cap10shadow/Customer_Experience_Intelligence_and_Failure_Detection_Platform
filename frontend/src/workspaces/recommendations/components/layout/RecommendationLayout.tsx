import type { ReactNode } from 'react'

import type { DecisionRecord } from '../../types'
import { RecommendationNavigator } from './RecommendationNavigator'
import styles from './RecommendationLayout.module.css'

export interface RecommendationLayoutProps {
  /** Undefined until Step 7.X G-01 provides a real, persisted decision -- never fabricated (Step 7.X A-07). */
  decision?: DecisionRecord
  children: ReactNode
}

/**
 * Composes the persistent `RecommendationNavigator` alongside the
 * single-column reading memo. Same responsive model as
 * `InvestigationLayout` (pure CSS switch at the 1024px threshold the
 * app's Sidebar already uses) -- desktop/laptop show navigator and
 * content side by side, tablet/mobile stack the navigator above the
 * content. Narrative order never changes; only this wrapping layout
 * adapts.
 */
export function RecommendationLayout({ decision, children }: RecommendationLayoutProps) {
  return (
    <div className={styles.layout}>
      <div className={styles.navigatorColumn}>
        <RecommendationNavigator decision={decision} />
      </div>
      <div className={styles.contentColumn}>{children}</div>
    </div>
  )
}
