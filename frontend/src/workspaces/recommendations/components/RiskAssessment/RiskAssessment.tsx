import { FutureCapabilityPlaceholder } from '@/shared/components/feedback'

import { RecommendationSection } from '../foundation'

export interface RiskAssessmentProps {
  isLoading?: boolean
}

/**
 * "What could go wrong?" -- UX-003: always a future-capability
 * placeholder, never "No Data" or "Empty." recommendation_service has no
 * risk-assessment capability today (Part 4's backend capability audit),
 * and the frozen architecture forbids deriving risk from priority/score
 * without an explicit backend contract for it.
 */
export function RiskAssessment({ isLoading = false }: RiskAssessmentProps) {
  return (
    <RecommendationSection id="risk-assessment" title="Risk Assessment" description="What could go wrong?">
      <FutureCapabilityPlaceholder
        title="Risk assessment is a future capability"
        description="What could go wrong with this recommendation will appear here once the recommendation engine begins assessing risk."
        isLoading={isLoading}
        loadingLabel="Loading risk assessment"
      />
    </RecommendationSection>
  )
}
