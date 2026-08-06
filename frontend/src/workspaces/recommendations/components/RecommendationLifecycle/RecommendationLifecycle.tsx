import { RecommendationSection } from '../foundation'
import type { DecisionRecord, LifecycleStage } from '../../types'
import { LifecycleSummary } from './LifecycleSummary'

export interface RecommendationLifecycleProps {
  decision: DecisionRecord
  currentStage?: LifecycleStage
  isLoading?: boolean
}

/**
 * Represents the recommendation after a decision has been made.
 * Decision Before Lifecycle: this section never shows lifecycle
 * progression for a recommendation that is still Pending Review -- see
 * `LifecycleSummary` for how each decision outcome is represented.
 */
export function RecommendationLifecycle({ decision, currentStage, isLoading = false }: RecommendationLifecycleProps) {
  return (
    <RecommendationSection id="lifecycle" title="Recommendation Lifecycle" description="What happens after the decision?">
      <LifecycleSummary decision={decision} currentStage={currentStage} isLoading={isLoading} />
    </RecommendationSection>
  )
}
