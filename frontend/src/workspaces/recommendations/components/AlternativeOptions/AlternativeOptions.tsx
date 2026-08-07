import { FutureCapabilityPlaceholder } from '@/shared/components/feedback'

import { RecommendationSection } from '../foundation'

export interface AlternativeOptionsProps {
  isLoading?: boolean
}

/**
 * "Why this recommendation instead of another?" -- UX-003: always a
 * future-capability placeholder in this step, never "No Data" or
 * "Empty." The Recommendation Decision Engine does not yet preserve
 * candidates it considered and did not select (REC-001), so there is
 * genuinely nothing to compare yet; that is a capability this section
 * is reserved for, not an absence of data for something the platform
 * already computes.
 */
export function AlternativeOptions({ isLoading = false }: AlternativeOptionsProps) {
  return (
    <RecommendationSection
      id="alternative-options"
      title="Alternative Options"
      description="Why this recommendation instead of another?"
    >
      <FutureCapabilityPlaceholder
        title="Alternative option comparison is a future capability"
        description="Comparing this recommendation against other options the platform considered will appear here once the recommendation engine begins preserving that comparison."
        isLoading={isLoading}
        loadingLabel="Loading alternative options"
      />
    </RecommendationSection>
  )
}
