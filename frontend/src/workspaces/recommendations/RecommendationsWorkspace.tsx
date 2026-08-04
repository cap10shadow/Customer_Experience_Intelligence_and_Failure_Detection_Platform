import { Grid, SectionContainer } from '@/shared/components/layout'
import { PlaceholderCard } from '@/shared/components/feedback'
import { WorkspaceContainer } from '@/shared/components/page'

/**
 * Recommendations -- lifecycle management, not discovery. Recommendations
 * are discovered inside the Dashboard, Action Center, and Investigations;
 * this workspace owns their lifecycle, history, and status once found
 * (and, in future phases, Human Actions/approvals/execution tracking).
 */
export function RecommendationsWorkspace() {
  return (
    <WorkspaceContainer
      title="Recommendations"
      description="Recommendation lifecycle management, history, and status."
    >
      <SectionContainer title="Recommendation queue" description="Open, in-progress, and historical recommendations across every incident.">
        <Grid minColumnWidth={240}>
          <PlaceholderCard title="Open recommendations" />
          <PlaceholderCard title="Recommendation history" />
          <PlaceholderCard title="Status overview" />
        </Grid>
      </SectionContainer>
    </WorkspaceContainer>
  )
}
