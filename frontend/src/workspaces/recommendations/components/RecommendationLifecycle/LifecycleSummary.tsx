import { Stack } from '@/shared/components/layout'
import { classNames } from '@/shared/utilities/classNames'

import { RecommendationEmptyState, RecommendationLoadingState } from '../foundation'
import { LIFECYCLE_STAGE_LABEL, LIFECYCLE_STAGE_ORDER, type DecisionRecord, type LifecycleStage } from '../../types'
import styles from './LifecycleSummary.module.css'

export interface LifecycleSummaryProps {
  decision: DecisionRecord
  /** Only meaningful once `decision.status === 'approved'`. */
  currentStage?: LifecycleStage
  isLoading?: boolean
}

/**
 * Decision Before Lifecycle, enforced structurally: this component
 * never renders the Approved → Awaiting Implementation → Outcome
 * Evaluation → Completed progression unless `decision.status` is
 * already 'approved'. Pending Review is not a lifecycle stage -- it is
 * the absence of one, communicated the same confident, explanatory way
 * every other "not yet" state in this platform is. Rejected and
 * Deferred are each represented on their own terms, not as a broken or
 * incomplete version of the Approved path.
 */
export function LifecycleSummary({ decision, currentStage, isLoading = false }: LifecycleSummaryProps) {
  if (isLoading) {
    return <RecommendationLoadingState label="Loading recommendation lifecycle" />
  }

  if (decision.status === 'pending-review') {
    return (
      <RecommendationEmptyState
        title="Lifecycle begins once a decision is made"
        description="This recommendation is still pending review. Its implementation and outcome lifecycle will appear here once it is approved."
      />
    )
  }

  if (decision.status === 'rejected') {
    return (
      <RecommendationEmptyState
        title="This recommendation was rejected"
        description="No further lifecycle applies. The decision above reflects why."
      />
    )
  }

  if (decision.status === 'deferred') {
    return (
      <RecommendationEmptyState
        title="This recommendation was deferred"
        description="Its lifecycle will begin only if it is approved after a later review."
      />
    )
  }

  return (
    <Stack gap={0} as="ol" className={styles.list}>
      {LIFECYCLE_STAGE_ORDER.map((stage, index) => {
        const isCurrent = stage === currentStage
        const isComplete = currentStage ? LIFECYCLE_STAGE_ORDER.indexOf(currentStage) > index : false
        return (
          <li key={stage} className={classNames(styles.stage, isCurrent && styles.current)}>
            <span className={styles.marker} aria-hidden="true" />
            <span>
              <span className={styles.stageLabel}>{LIFECYCLE_STAGE_LABEL[stage]}</span>
              {isCurrent ? <span className={styles.stageStatus}> — current stage</span> : null}
              {isComplete ? <span className={styles.stageStatus}> — complete</span> : null}
            </span>
          </li>
        )
      })}
    </Stack>
  )
}
