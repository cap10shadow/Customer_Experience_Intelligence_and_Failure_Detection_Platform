import { Badge, type BadgeTone } from '@/shared/components/utility'
import { Panel, Stack } from '@/shared/components/layout'

import { ConfidencePresentation, InvestigationLoadingState } from '../foundation'
import { ROOT_CAUSE_STATUS_LABEL, type RootCauseExplanation } from '../../types'
import styles from './RootCauseCard.module.css'

export interface RootCauseCardProps {
  explanation: RootCauseExplanation
  isLoading?: boolean
}

const STATUS_TONE: Record<RootCauseExplanation['status'], BadgeTone> = {
  identified: 'neutral',
  confirmed: 'success',
  rejected: 'critical',
}

/**
 * "Why did this happen?" -- presented as reasoning, not a verdict. The
 * confidence value here measures rule certainty specifically (see
 * `ConfidencePresentation`) and must never be read alongside Business
 * Impact's confidence as though they were the same scale. The status
 * Badge reflects the real root_cause_service lifecycle state
 * (identified/confirmed/rejected), now that RootCauseAnalysis offers
 * real confirm/reject/refresh actions -- see `RootCauseActions`.
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
        <div className={styles.headlineRow}>
          <p className={styles.headline}>{explanation.headline}</p>
          <Badge tone={STATUS_TONE[explanation.status]}>{ROOT_CAUSE_STATUS_LABEL[explanation.status]}</Badge>
        </div>
        <p className={styles.reasoning}>{explanation.reasoning}</p>
        <ConfidencePresentation level={explanation.confidenceLevel} measures="root cause rule certainty" />
      </Stack>
    </Panel>
  )
}
