import { Panel, Stack } from '@/shared/components/layout'

import { RecommendationLoadingState } from '../foundation'
import type { RationaleReason } from '../../types'
import styles from './RationaleCard.module.css'

export interface RationaleCardProps {
  reason: RationaleReason
  isLoading?: boolean
}

/** "Why is this recommended?" -- references what the investigation already established, never repeats it. */
export function RationaleCard({ reason, isLoading = false }: RationaleCardProps) {
  if (isLoading) {
    return (
      <Panel>
        <RecommendationLoadingState label="Loading recommendation rationale" />
      </Panel>
    )
  }

  return (
    <Panel>
      <Stack gap={2}>
        <p className={styles.headline}>{reason.headline}</p>
        <p className={styles.explanation}>{reason.explanation}</p>
      </Stack>
    </Panel>
  )
}
