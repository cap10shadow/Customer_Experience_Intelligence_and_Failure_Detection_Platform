import { InvestigationSection } from '../foundation'
import { ObservationCard } from './ObservationCard'

const DEFAULT_HEADLINE = 'Payment failure rate is trending outside its typical range'
const DEFAULT_DESCRIPTION =
  'Checkout attempts have been failing more often than the recent baseline for this operational window. This section will describe the detected change itself, before any explanation is offered.'

export interface ObservationProps {
  /** Defaults to illustrative content -- InvestigationsWorkspace passes real, Gateway-sourced values here instead of editing this component. */
  headline?: string
  description?: string
  isLoading?: boolean
}

/** "What happened?" -- the investigation's opening statement, purely factual, before any evidence, cause, or judgment is introduced. */
export function Observation({ headline = DEFAULT_HEADLINE, description = DEFAULT_DESCRIPTION, isLoading = false }: ObservationProps) {
  return (
    <InvestigationSection id="observation" title="Observation" description="What happened?">
      <ObservationCard headline={headline} description={description} isLoading={isLoading} />
    </InvestigationSection>
  )
}
