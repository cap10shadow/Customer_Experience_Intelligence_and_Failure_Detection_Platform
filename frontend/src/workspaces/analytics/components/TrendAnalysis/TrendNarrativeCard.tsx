import { Panel, Stack } from '@/shared/components/layout'
import { Icon } from '@/shared/icons'

import { AnalyticsLoadingState } from '../foundation'
import type { TrendNarrative } from '../../types'
import styles from './TrendNarrativeCard.module.css'

export interface TrendNarrativeCardProps {
  trend: TrendNarrative
  isLoading?: boolean
}

/**
 * Trend → Narrative → Supporting Evidence -- never Chart → Interpretation.
 * The trend is stated in words first; the reserved chart area at the
 * bottom is deliberately small and de-emphasized, the same "future
 * chart" extension point Dashboard's `EvidenceSection` established in
 * Phase 10 Step 2, never the section's primary content.
 */
export function TrendNarrativeCard({ trend, isLoading = false }: TrendNarrativeCardProps) {
  if (isLoading) {
    return (
      <Panel>
        <AnalyticsLoadingState label="Loading trend" />
      </Panel>
    )
  }

  return (
    <Panel>
      <Stack gap={3}>
        <p className={styles.trend}>{trend.trend}</p>
        <p className={styles.narrative}>{trend.narrative}</p>
        <div className={styles.evidence}>
          <div className={styles.chartArea} aria-hidden="true">
            <Icon name="trendUp" size={20} />
          </div>
          <p className={styles.evidenceText}>{trend.evidence}</p>
        </div>
      </Stack>
    </Panel>
  )
}
