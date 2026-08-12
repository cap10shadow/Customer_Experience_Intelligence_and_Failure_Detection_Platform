import { FutureCapabilityPlaceholder } from '@/shared/components/feedback'

import { RecommendationSection } from '../foundation'
import type { DecisionRecord, LifecycleStage } from '../../types'
import { LifecycleSummary } from './LifecycleSummary'

export interface RecommendationLifecycleProps {
  /** Undefined until Step 7.X G-01 provides a real, persisted decision -- never fabricated (Step 7.X A-07). */
  decision?: DecisionRecord
  currentStage?: LifecycleStage
  isLoading?: boolean
}

/**
 * Represents the recommendation after a decision has been made.
 * Decision Before Lifecycle: this section never shows lifecycle
 * progression for a recommendation that is still Pending Review -- see
 * `LifecycleSummary` for how each decision outcome is represented.
 *
 * Step 7.X A-07: renders an honest `FutureCapabilityPlaceholder` until
 * `decision` is real, rather than a fabricated "still pending review"
 * lifecycle state -- no backend capability persists a decision yet
 * (that is Step 7.X G-01), so there is genuinely no lifecycle state to
 * describe, not merely an empty one.
 */
export function RecommendationLifecycle({ decision, currentStage, isLoading = false }: RecommendationLifecycleProps) {
  return (
    <RecommendationSection id="lifecycle" title="Recommendation Lifecycle" description="What happens after the decision?">
      {decision ? (
        <LifecycleSummary decision={decision} currentStage={currentStage} isLoading={isLoading} />
      ) : (
        <FutureCapabilityPlaceholder
          title="Recommendation lifecycle tracking is a future capability"
          description="Implementation status and outcome tracking will appear here once the platform persists a decision for this recommendation."
          isLoading={isLoading}
          loadingLabel="Loading recommendation lifecycle"
        />
      )}
    </RecommendationSection>
  )
}
