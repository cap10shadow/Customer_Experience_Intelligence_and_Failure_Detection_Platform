import { FutureCapabilityPlaceholder } from '@/shared/components/feedback'

import { AnalyticsSection } from '../foundation'

export interface OrganizationalInsightsProps {
  isLoading?: boolean
}

/**
 * "What has the organization learned?" -- Step 7.X G-02: always a
 * future-capability placeholder, reusing the exact component
 * Recommendation Effectiveness already established. Synthesizing a
 * supported conclusion requires real Pattern Discovery and
 * Recommendation Effectiveness evidence to draw from -- neither exists
 * yet, so there is genuinely nothing to synthesize, not an absence of
 * data for something the platform already computes. `isLoading`
 * defaults to false and is never wired to a real fetch: this section
 * has no backend data dependency.
 */
export function OrganizationalInsights({ isLoading = false }: OrganizationalInsightsProps) {
  return (
    <AnalyticsSection id="organizational-insights" title="Organizational Insights" description="What has the organization learned?">
      <FutureCapabilityPlaceholder
        title="Organizational insights are a future capability"
        description="Conclusions synthesized from trend and pattern evidence across the organization will appear here once that evidence exists to draw from."
        isLoading={isLoading}
        loadingLabel="Loading organizational insights"
      />
    </AnalyticsSection>
  )
}
