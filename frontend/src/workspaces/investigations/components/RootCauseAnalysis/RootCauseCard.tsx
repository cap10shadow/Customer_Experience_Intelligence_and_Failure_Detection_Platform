import { Panel, Stack } from '@/shared/components/layout'

import { ConfidencePresentation, InvestigationLoadingState } from '../foundation'
import type { RootCauseExplanation } from '../../types'
import styles from './RootCauseCard.module.css'

export interface RootCauseCardProps {
  explanation: RootCauseExplanation
  isLoading?: boolean
}

/**
 * "Why did this happen?" -- presented as reasoning, not a verdict. The
 * confidence value here measures rule certainty specifically (see
 * `ConfidencePresentation`) and must never be read alongside Business
 * Impact's confidence as though they were the same scale.
 */
export function RootCauseCard({ explanation, isLoading = false }: RootCauseCardProps) {
  if (isLoading) {
    return (
      <Panel>
        <InvestigationLoadingState label="Loading root cause analysis" />
      </Panel>
    )
  }

  return (
    <Panel>
      <Stack gap={3}>
        <p className={styles.headline}>{explanation.headline}</p>
        <p className={styles.reasoning}>{explanation.reasoning}</p>
        <ConfidencePresentation level={explanation.confidenceLevel} measures="root cause rule certainty" />
      </Stack>
    </Panel>
  )
}
