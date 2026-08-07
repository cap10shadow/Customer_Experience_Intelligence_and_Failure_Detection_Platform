import { FutureCapabilityPlaceholder } from '@/shared/components/feedback'

import { AnalyticsSection } from '../foundation'

export interface RecommendationEffectivenessProps {
  isLoading?: boolean
}

/**
 * "Did our decisions improve the organization?" -- always a
 * future-capability placeholder in this step (UX-007), reusing the
 * exact component Recommendation Workspace's Alternative Options
 * already established, never a new one. Recommendation outcome
 * tracking does not exist anywhere in the platform yet -- per ARB-002,
 * Outcome is a long-term-vision pipeline stage, not an implemented
 * capability -- so there is genuinely nothing to aggregate across
 * recommendations yet. This evaluates many recommendations
 * collectively; it does not own any single recommendation's lifecycle,
 * which remains Recommendations' responsibility alone.
 */
export function RecommendationEffectiveness({ isLoading = false }: RecommendationEffectivenessProps) {
  return (
    <AnalyticsSection
      id="recommendation-effectiveness"
      title="Recommendation Effectiveness"
      description="Did our decisions improve the organization?"
    >
      <FutureCapabilityPlaceholder
        title="Recommendation effectiveness is a future capability"
        description="Evaluating whether recommendations improved organizational outcomes will appear here once outcome tracking exists across the platform."
        isLoading={isLoading}
        loadingLabel="Loading recommendation effectiveness"
      />
    </AnalyticsSection>
  )
}
