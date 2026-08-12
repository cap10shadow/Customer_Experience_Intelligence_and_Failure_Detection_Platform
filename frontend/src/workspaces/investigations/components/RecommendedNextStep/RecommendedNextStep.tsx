import { InvestigationEmptyState, InvestigationSection } from '../foundation'
import type { RecommendedAction } from '../../types'
import { RecommendationSummary } from './RecommendationSummary'

const DEFAULT_RECOMMENDED_ACTION: RecommendedAction = {
  headline: 'Review the recent payment provider change',
  reason: 'Confirming or ruling out the provider change would validate this investigation\'s root cause before further action is taken.',
  recommendationId: 'illustrative-recommendation-id',
}

export interface RecommendedNextStepProps {
  /** Defaults to illustrative content -- InvestigationsWorkspace passes a real recommended action here instead of editing this component. Explicit `null` means no recommendation has been generated for this incident yet -- a real domain state, rendered as an honest empty state. */
  action?: RecommendedAction | null
  isLoading?: boolean
}

/**
 * "What should happen next?" -- summarizes only. Approval, rejection,
 * implementation tracking, and monitoring all belong to Recommendations
 * (FE-001); this section's only responsibility is the transition.
 */
export function RecommendedNextStep({ action = DEFAULT_RECOMMENDED_ACTION, isLoading = false }: RecommendedNextStepProps) {
  return (
    <InvestigationSection id="recommended-next-step" title="Recommended Next Step" description="What should happen next?">
      {!isLoading && action === null ? (
        <InvestigationEmptyState
          title="No recommendation has been generated yet"
          description="This investigation hasn't produced a recommended next step yet. This section updates as soon as one has been generated for this incident."
        />
      ) : (
        <RecommendationSummary action={action ?? DEFAULT_RECOMMENDED_ACTION} isLoading={isLoading} />
      )}
    </InvestigationSection>
  )
}
