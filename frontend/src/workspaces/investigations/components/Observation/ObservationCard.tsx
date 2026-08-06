import { Panel } from '@/shared/components/layout'

import { InvestigationLoadingState } from '../foundation'
import styles from './ObservationCard.module.css'

export interface ObservationCardProps {
  headline: string
  description: string
  isLoading?: boolean
}

/** A single factual statement of what changed -- no cause, no severity judgment, no number that hasn't actually been computed. Root Cause Analysis owns "why"; this owns only "what." */
export function ObservationCard({ headline, description, isLoading = false }: ObservationCardProps) {
  return (
    <Panel className={styles.card}>
      {isLoading ? (
        <InvestigationLoadingState label="Loading observation" />
      ) : (
        <>
          <p className={styles.headline}>{headline}</p>
          <p className={styles.description}>{description}</p>
        </>
      )}
    </Panel>
  )
}
