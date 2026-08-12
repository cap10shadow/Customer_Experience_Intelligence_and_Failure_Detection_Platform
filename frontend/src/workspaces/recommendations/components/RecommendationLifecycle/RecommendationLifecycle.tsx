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
 * `decision` is real, persisted state since Step 7.X G-01. This
 * component still renders an honest `FutureCapabilityPlaceholder`
 * whenever `decision` is undefined -- now meaning "no decision has been
 * recorded for this Recommendation yet" (a real, current fact) rather
 * than "no backend capability exists yet". Lifecycle stage tracking
 * itself (Awaiting Implementation / Outcome Evaluation / Completed)
 * remains out of scope -- `currentStage` has no real backend source and
 * is never fabricated by this workspace.
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
