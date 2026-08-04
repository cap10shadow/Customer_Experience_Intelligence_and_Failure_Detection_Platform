import { Panel, Stack } from '@/shared/components/layout'

import { DashboardDrillDownLink, DashboardLoadingState } from '../foundation'
import type { OperationalStory } from '../../types'
import styles from './OperationalStoryCard.module.css'

export interface OperationalStoryCardProps {
  story: OperationalStory
  isLoading?: boolean
}

/**
 * The Dashboard's presentation of one Incident lifecycle as a single
 * continuous narrative -- Complaint → Incident → Root Cause → Business
 * Impact → Recommendation, told as a story rather than a database
 * record. No raw entity id is ever shown; the drill-down link is the
 * only bridge to the Investigations workspace, which owns the record.
 */
export function OperationalStoryCard({ story, isLoading = false }: OperationalStoryCardProps) {
  if (isLoading) {
    return (
      <Panel as="article">
        <DashboardLoadingState label="Loading operational story" />
      </Panel>
    )
  }

  return (
    <Panel as="article" className={styles.card}>
      <Stack gap={2}>
        <h3 className={styles.headline}>{story.headline}</h3>
        <p className={styles.situation}>{story.situation}</p>
        <p className={styles.significance}>
          <span className={styles.fieldLabel}>Why it matters: </span>
          {story.significance}
        </p>
        <p className={styles.direction}>
          <span className={styles.fieldLabel}>Investigation direction: </span>
          {story.direction}
        </p>
        <p className={styles.context}>{story.context}</p>
        {story.drillDownPath ? (
          <DashboardDrillDownLink to={story.drillDownPath} label={story.drillDownLabel ?? 'Explore this story'} />
        ) : null}
      </Stack>
    </Panel>
  )
}
