import { Stack } from '@/shared/components/layout'

import type { RecommendationDecisionApiValue } from '../../api'
import { RecommendationSection } from '../foundation'
import type { DecisionRecord, DecisionStatus } from '../../types'
import { DecisionForm } from './DecisionForm'
import { DecisionSummary } from './DecisionSummary'

/** The inverse of viewModel.ts's toDecisionStatus() -- 'pending-review' maps back to the backend's 'pending'; every other value is already a 1:1 match. */
function toApiDecisionValue(status: DecisionStatus): RecommendationDecisionApiValue {
  return status === 'pending-review' ? 'pending' : status
}

export interface DecisionProps {
  /** Undefined until a real decision has been persisted (Step 7.X G-01) -- never fabricated (Step 7.X A-07). */
  decision?: DecisionRecord
  isLoading?: boolean
  isSubmitting?: boolean
  submitErrorMessage?: string
  onSubmitDecision?: (decision: RecommendationDecisionApiValue, note: string | undefined) => void
}

/**
 * Represents the human decision -- and, since Step 7.X G-01, the one
 * real write capability this workspace has: recording it. No approval
 * workflow, no actor/owner, no multi-step sign-off exists here or
 * anywhere in this step, per G-01's explicitly minimal scope.
 * `DecisionForm` always renders (not just when no decision exists yet)
 * since a decision can be changed -- see the form's own docstring for
 * why repeated submission simply overwrites.
 */
export function Decision({
  decision,
  isLoading = false,
  isSubmitting = false,
  submitErrorMessage,
  onSubmitDecision,
}: DecisionProps) {
  return (
    <RecommendationSection id="decision" title="Decision" description="What has been decided?">
      <Stack gap={4}>
        {decision ? <DecisionSummary decision={decision} isLoading={isLoading} /> : null}
        {onSubmitDecision ? (
          <DecisionForm
            currentDecision={decision ? toApiDecisionValue(decision.status) : undefined}
            isSubmitting={isSubmitting}
            errorMessage={submitErrorMessage}
            onSubmit={onSubmitDecision}
          />
        ) : null}
      </Stack>
    </RecommendationSection>
  )
}
