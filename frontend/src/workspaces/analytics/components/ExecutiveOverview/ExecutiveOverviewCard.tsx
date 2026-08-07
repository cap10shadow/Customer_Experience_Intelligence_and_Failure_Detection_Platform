import { Panel } from '@/shared/components/layout'

import { AnalyticsLoadingState } from '../foundation'
import type { ObservationItem } from '../../types'
import styles from './ExecutiveOverviewCard.module.css'

export interface ExecutiveOverviewCardProps {
  observation: ObservationItem
  isLoading?: boolean
}

/**
 * One descriptive observation for the selected analysis period --
 * deliberately factual, never evaluative. "Complaint volume moved from
 * X to Y" belongs here; "our response improved" does not -- that
 * judgment belongs to Organizational Insights, only after Trend
 * Analysis, Pattern Discovery, and Recommendation Effectiveness have
 * presented the evidence for it.
 */
export function ExecutiveOverviewCard({ observation, isLoading = false }: ExecutiveOverviewCardProps) {
  if (isLoading) {
    return (
      <Panel>
        <AnalyticsLoadingState label="Loading observation" />
      </Panel>
    )
  }

  return (
    <Panel>
      <p className={styles.headline}>{observation.headline}</p>
      <p className={styles.detail}>{observation.detail}</p>
    </Panel>
  )
}
