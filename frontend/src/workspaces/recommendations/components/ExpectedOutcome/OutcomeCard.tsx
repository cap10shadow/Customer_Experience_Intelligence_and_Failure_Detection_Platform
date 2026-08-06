import { Panel } from '@/shared/components/layout'

import { RecommendationLoadingState } from '../foundation'
import type { OutcomeItem } from '../../types'
import styles from './OutcomeCard.module.css'

export interface OutcomeCardProps {
  outcome: OutcomeItem
  isLoading?: boolean
}

/** One expected improvement -- always framed as an outcome to expect, never a guarantee or a metric that hasn't actually been computed. */
export function OutcomeCard({ outcome, isLoading = false }: OutcomeCardProps) {
  if (isLoading) {
    return (
      <Panel>
        <RecommendationLoadingState label="Loading expected outcome" />
      </Panel>
    )
  }

  return (
    <Panel>
      <p className={styles.headline}>{outcome.headline}</p>
      <p className={styles.detail}>{outcome.detail}</p>
    </Panel>
  )
}
