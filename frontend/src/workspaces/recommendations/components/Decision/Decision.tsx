import { RecommendationSection } from '../foundation'
import type { DecisionRecord } from '../../types'
import { DecisionSummary } from './DecisionSummary'

export interface DecisionProps {
  decision: DecisionRecord
  isLoading?: boolean
}

/** Represents the human decision. Architectural responsibility only -- no approval, rejection, or workflow controls exist here or anywhere in this step. */
export function Decision({ decision, isLoading = false }: DecisionProps) {
  return (
    <RecommendationSection id="decision" title="Decision" description="What has been decided?">
      <DecisionSummary decision={decision} isLoading={isLoading} />
    </RecommendationSection>
  )
}
