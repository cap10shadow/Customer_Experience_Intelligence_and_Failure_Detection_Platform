import { AdvisoryNotice } from '@/shared/components/feedback'
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
  /**
   * Whether this session holds the `operator` role the Gateway requires
   * to record a decision. Supplied by `RecommendationsWorkspace` (which
   * reads it from `AuthContext`) rather than read from context here, so
   * this stays a presentational component the way every other section in
   * this workspace is -- and so it remains renderable standalone.
   * Defaults to `true`: a caller that says nothing about roles gets the
   * pre-existing behaviour, never a spurious restriction notice.
   */
  canRecordDecision?: boolean
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
 *
 * Role awareness (this pass): `PATCH /recommendations/{id}/decision`
 * requires `operator` at the Gateway. A `viewer` previously saw an
 * identical, fully-enabled form and only discovered the restriction as a
 * `403` *after* composing and submitting a decision. The form is still
 * rendered rather than hidden -- the Gateway remains the authorization
 * boundary and frontend visibility is explicitly not authorization (§12
 * of the frozen architecture) -- but the restriction is now stated up
 * front instead of being discovered by failure.
 */
export function Decision({
  decision,
  isLoading = false,
  isSubmitting = false,
  submitErrorMessage,
  canRecordDecision = true,
  onSubmitDecision,
}: DecisionProps) {
  return (
    <RecommendationSection id="decision" title="Decision" description="What has been decided?">
      <Stack gap={4}>
        {decision ? <DecisionSummary decision={decision} isLoading={isLoading} /> : null}
        {onSubmitDecision && !canRecordDecision ? (
          <AdvisoryNotice
            title="Recording a decision requires the operator role"
            description="Your account holds read access to this recommendation. Submitting the form below will be refused by the platform; an operator or administrator can record the decision."
          />
        ) : null}
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
