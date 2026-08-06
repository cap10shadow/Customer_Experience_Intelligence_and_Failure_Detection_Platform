import { Panel, Stack } from '@/shared/components/layout'
import { StatusIndicator } from '@/shared/components/utility'

import { RecommendationLoadingState } from '../foundation'
import { DECISION_STATUS_LABEL, DECISION_STATUS_TONE, type DecisionRecord } from '../../types'
import styles from './DecisionSummary.module.css'

export interface DecisionSummaryProps {
  decision: DecisionRecord
  isLoading?: boolean
}

/**
 * Represents the human decision as data only -- no approve/reject
 * controls. This step reviews architectural responsibility, not UI
 * controls (per the frozen review); the workspace's job here is to make
 * the decision legible, not to collect one. 'rejected' deliberately
 * shares the same neutral tone as 'pending-review' and 'deferred' --
 * only 'approved' uses the success tone, since a past decision is
 * informational, never an alarm.
 */
export function DecisionSummary({ decision, isLoading = false }: DecisionSummaryProps) {
  if (isLoading) {
    return (
      <Panel>
        <RecommendationLoadingState label="Loading decision" />
      </Panel>
    )
  }

  return (
    <Panel>
      <Stack gap={2}>
        <StatusIndicator tone={DECISION_STATUS_TONE[decision.status]} label={DECISION_STATUS_LABEL[decision.status]} />
        <p className={styles.note}>{decision.note}</p>
      </Stack>
    </Panel>
  )
}
