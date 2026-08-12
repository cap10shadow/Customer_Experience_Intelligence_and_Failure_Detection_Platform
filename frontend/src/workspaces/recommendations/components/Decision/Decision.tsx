import { FutureCapabilityPlaceholder } from '@/shared/components/feedback'

import { RecommendationSection } from '../foundation'
import type { DecisionRecord } from '../../types'
import { DecisionSummary } from './DecisionSummary'

export interface DecisionProps {
  /** Undefined until Step 7.X G-01 provides a real, persisted decision -- never fabricated (Step 7.X A-07). */
  decision?: DecisionRecord
  isLoading?: boolean
}

/**
 * Represents the human decision. Architectural responsibility only --
 * no approval, rejection, or workflow controls exist here or anywhere
 * in this step. Step 7.X A-07: renders an honest
 * `FutureCapabilityPlaceholder` (matching Alternative Options' exact
 * pattern) until `decision` is real, rather than a fabricated "Pending
 * Review" status -- no backend capability persists a decision yet
 * (that is Step 7.X G-01).
 */
export function Decision({ decision, isLoading = false }: DecisionProps) {
  return (
    <RecommendationSection id="decision" title="Decision" description="What has been decided?">
      {decision ? (
        <DecisionSummary decision={decision} isLoading={isLoading} />
      ) : (
        <FutureCapabilityPlaceholder
          title="Decision capture is a future capability"
          description="Recording a human decision (approve, reject, or defer) for this recommendation will appear here once the platform persists that decision."
          isLoading={isLoading}
          loadingLabel="Loading decision"
        />
      )}
    </RecommendationSection>
  )
}
