import { Grid } from '@/shared/components/layout'

import { RecommendationSection } from '../foundation'
import type { OutcomeItem } from '../../types'
import { OutcomeCard } from './OutcomeCard'

const OUTCOMES: OutcomeItem[] = [
  { id: 'operational', headline: 'Operational improvement', detail: 'Checkout should return to its normal success rate once the cause is addressed.' },
  { id: 'customer', headline: 'Customer improvement', detail: 'Fewer customers should encounter a failed payment at checkout.' },
  { id: 'financial', headline: 'Financial improvement', detail: 'Recovered transactions that are currently failing at checkout.' },
  { id: 'risk-reduction', headline: 'Risk reduction', detail: 'Reduces the chance of the issue escalating into a larger service disruption.' },
]

export interface ExpectedOutcomeProps {
  isLoading?: boolean
}

/** "What should improve?" -- expected improvement only, never a guarantee. */
export function ExpectedOutcome({ isLoading = false }: ExpectedOutcomeProps) {
  return (
    <RecommendationSection id="expected-outcome" title="Expected Outcome" description="What should improve?">
      <Grid minColumnWidth={220}>
        {OUTCOMES.map((outcome) => (
          <OutcomeCard key={outcome.id} outcome={outcome} isLoading={isLoading} />
        ))}
      </Grid>
    </RecommendationSection>
  )
}
