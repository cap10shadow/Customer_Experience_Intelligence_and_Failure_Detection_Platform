import { InvestigationSection } from '../foundation'
import { ObservationCard } from './ObservationCard'

export interface ObservationProps {
  isLoading?: boolean
}

/** "What happened?" -- the investigation's opening statement, purely factual, before any evidence, cause, or judgment is introduced. */
export function Observation({ isLoading = false }: ObservationProps) {
  return (
    <InvestigationSection id="observation" title="Observation" description="What happened?">
      <ObservationCard
        headline="Payment failure rate is trending outside its typical range"
        description="Checkout attempts have been failing more often than the recent baseline for this operational window. This section will describe the detected change itself, before any explanation is offered."
        isLoading={isLoading}
      />
    </InvestigationSection>
  )
}
