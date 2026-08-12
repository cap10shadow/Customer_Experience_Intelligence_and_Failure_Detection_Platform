import { FutureCapabilityPlaceholder } from '@/shared/components/feedback'

import { RecommendationSection } from '../foundation'

export interface ExpectedOutcomeProps {
  isLoading?: boolean
}

/**
 * "What should improve?" -- UX-003: always a future-capability
 * placeholder, never "No Data" or "Empty." recommendation_service has no
 * expected-outcome or outcome-tracking capability today (Part 4's backend
 * capability audit) -- there is genuinely nothing to draw on yet, so
 * nothing is fabricated here.
 */
export function ExpectedOutcome({ isLoading = false }: ExpectedOutcomeProps) {
  return (
    <RecommendationSection id="expected-outcome" title="Expected Outcome" description="What should improve?">
      <FutureCapabilityPlaceholder
        title="Expected outcome tracking is a future capability"
        description="What should improve once this recommendation is acted on will appear here once the platform begins tracking expected and actual outcomes."
        isLoading={isLoading}
        loadingLabel="Loading expected outcome"
      />
    </RecommendationSection>
  )
}
