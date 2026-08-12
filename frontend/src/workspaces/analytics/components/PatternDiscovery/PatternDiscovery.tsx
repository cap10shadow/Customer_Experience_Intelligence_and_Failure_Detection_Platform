import { FutureCapabilityPlaceholder } from '@/shared/components/feedback'

import { AnalyticsSection } from '../foundation'

export interface PatternDiscoveryProps {
  isLoading?: boolean
}

/**
 * "What keeps happening?" -- Step 7.X G-02: always a future-capability
 * placeholder, reusing the exact component Recommendation Effectiveness
 * (and Recommendation Workspace's Alternative Options before it) already
 * established. No backend capability detects or preserves recurring
 * patterns anywhere in the platform today -- there is genuinely nothing
 * to synthesize a narrative from yet, not an empty result for something
 * the platform already computes. `isLoading` defaults to false and is
 * never wired to a real fetch: this section has no backend data
 * dependency, so it renders honestly rather than pretending to wait on
 * an API that doesn't back it.
 */
export function PatternDiscovery({ isLoading = false }: PatternDiscoveryProps) {
  return (
    <AnalyticsSection id="pattern-discovery" title="Pattern Discovery" description="What keeps happening?">
      <FutureCapabilityPlaceholder
        title="Pattern discovery is a future capability"
        description="Identifying recurring patterns across incidents over time will appear here once the platform detects and preserves them."
        isLoading={isLoading}
        loadingLabel="Loading pattern discovery"
      />
    </AnalyticsSection>
  )
}
