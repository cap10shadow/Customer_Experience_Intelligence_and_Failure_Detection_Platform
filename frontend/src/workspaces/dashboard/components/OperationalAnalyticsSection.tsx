import { Grid, SectionContainer } from '@/shared/components/layout'
import { PlaceholderCard } from '@/shared/components/feedback'

/**
 * Section 4: supporting metrics and analytical context -- deliberately
 * placed last. Home leads with what changed and what needs a decision;
 * charts support that story, they never define it.
 */
export function OperationalAnalyticsSection() {
  return (
    <SectionContainer
      title="Operational Analytics"
      description="Supporting metrics and analytical context for the situation above."
    >
      <Grid minColumnWidth={220}>
        <PlaceholderCard title="Complaint volume trend" />
        <PlaceholderCard title="Anomaly frequency" />
        <PlaceholderCard title="Resolution velocity" />
      </Grid>
    </SectionContainer>
  )
}
