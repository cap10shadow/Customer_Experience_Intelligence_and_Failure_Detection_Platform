import { FutureCapabilityPlaceholder } from '@/shared/components/feedback'

import { AnalyticsSection } from '../foundation'

export interface StrategicOpportunitiesProps {
  isLoading?: boolean
}

/**
 * "Where should the organization consider investing next?" -- Step 7.X
 * G-02: always a future-capability placeholder, reusing the exact
 * component Recommendation Effectiveness already established.
 * Organization-level opportunities would need to be derived from real
 * Organizational Insights -- which does not exist yet -- so there is
 * genuinely nothing to identify. This section never approves actions,
 * assigns work, creates initiatives, or manages a lifecycle --
 * Recommendation Workspace remains the platform's only Decision
 * Workspace. `isLoading` defaults to false and is never wired to a real
 * fetch: this section has no backend data dependency.
 */
export function StrategicOpportunities({ isLoading = false }: StrategicOpportunitiesProps) {
  return (
    <AnalyticsSection
      id="strategic-opportunities"
      title="Strategic Opportunities"
      description="Where should the organization consider investing next?"
    >
      <FutureCapabilityPlaceholder
        title="Strategic opportunity identification is a future capability"
        description="Organization-level opportunities identified from accumulated insights will appear here once organizational insights exist to draw from."
        isLoading={isLoading}
        loadingLabel="Loading strategic opportunities"
      />
    </AnalyticsSection>
  )
}
