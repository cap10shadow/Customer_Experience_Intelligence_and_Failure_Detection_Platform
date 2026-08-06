import { Panel, Stack } from '@/shared/components/layout'
import { Badge } from '@/shared/components/utility'

import { RecommendationLoadingState } from '../foundation'
import type { RecommendationOverview } from '../../types'
import styles from './RecommendationOverviewCard.module.css'

export interface RecommendationOverviewCardProps {
  overview: RecommendationOverview
  isLoading?: boolean
}

/** "What is being recommended?" -- the memo's opening statement: headline, plain-language summary, and its category/priority as calm labels, not alarm colors. */
export function RecommendationOverviewCard({ overview, isLoading = false }: RecommendationOverviewCardProps) {
  if (isLoading) {
    return (
      <Panel>
        <RecommendationLoadingState label="Loading recommendation overview" />
      </Panel>
    )
  }

  return (
    <Panel>
      <Stack gap={3}>
        <div className={styles.tags}>
          <Badge tone="accent">{overview.category}</Badge>
          <Badge tone="neutral">{overview.priority} priority</Badge>
        </div>
        <p className={styles.headline}>{overview.headline}</p>
        <p className={styles.summary}>{overview.summary}</p>
      </Stack>
    </Panel>
  )
}
