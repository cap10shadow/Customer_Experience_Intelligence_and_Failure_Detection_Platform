import { InvestigationSection } from '../foundation'
import type { RecommendedAction } from '../../types'
import { RecommendationSummary } from './RecommendationSummary'

const RECOMMENDED_ACTION: RecommendedAction = {
  headline: 'Review the recent payment provider change',
  reason: 'Confirming or ruling out the provider change would validate this investigation\'s root cause before further action is taken.',
  recommendationId: 'illustrative-recommendation-id',
}

export interface RecommendedNextStepProps {
  isLoading?: boolean
}

/**
 * "What should happen next?" -- summarizes only. Approval, rejection,
 * implementation tracking, and monitoring all belong to Recommendations
 * (FE-001); this section's only responsibility is the transition.
 */
export function RecommendedNextStep({ isLoading = false }: RecommendedNextStepProps) {
  return (
    <InvestigationSection id="recommended-next-step" title="Recommended Next Step" description="What should happen next?">
      <RecommendationSummary action={RECOMMENDED_ACTION} isLoading={isLoading} />
    </InvestigationSection>
  )
}
