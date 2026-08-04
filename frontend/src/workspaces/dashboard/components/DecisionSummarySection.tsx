import { Grid, SectionContainer } from '@/shared/components/layout'
import { PlaceholderCard } from '@/shared/components/feedback'

/**
 * Section 2: highlights operational intelligence requiring a decision
 * ("why does it matter?", "what requires attention?") -- e.g. a future
 * summary of high-priority Recommendations. Structure only; no
 * Recommendation data is fetched or fabricated here.
 */
export function DecisionSummarySection() {
  return (
    <SectionContainer
      title="Decision Summary"
      description="Operational intelligence that currently requires a decision, ranked by urgency."
    >
      <Grid minColumnWidth={240}>
        <PlaceholderCard title="Highest-priority recommendation" description="Populated from the Recommendation Service in a future step." />
        <PlaceholderCard title="Emerging risk" description="Populated from Business Impact intelligence in a future step." />
        <PlaceholderCard title="Unresolved investigation" description="Populated from active Investigations in a future step." />
      </Grid>
    </SectionContainer>
  )
}
