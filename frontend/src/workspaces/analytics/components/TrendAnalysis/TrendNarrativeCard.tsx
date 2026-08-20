import { Panel, Stack } from '@/shared/components/layout'

import { AnalyticsLoadingState } from '../foundation'
import type { TrendNarrative } from '../../types'
import styles from './TrendNarrativeCard.module.css'

export interface TrendNarrativeCardProps {
  trend: TrendNarrative
  isLoading?: boolean
}

/**
 * Trend → Narrative → Supporting Evidence -- never Chart →
 * Interpretation. The trend is stated in words first.
 *
 * The small dashed "reserved chart area" this card used to render was
 * removed once real charts existed: it was a decorative `trendUp` icon
 * in a placeholder box, which read as a thumbnail of a chart that had
 * never been drawn from anything. The real charts now live one level up,
 * in `TrendVisualization`, where they are drawn from actual returned
 * series.
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
          <p className={styles.evidenceText}>{trend.evidence}</p>
        </div>
      </Stack>
    </Panel>
  )
}
