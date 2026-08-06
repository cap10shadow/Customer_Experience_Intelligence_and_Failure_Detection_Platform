import { Grid, SectionContainer, Stack } from '@/shared/components/layout'
import { PlaceholderCard } from '@/shared/components/feedback'
import { WorkspaceContainer } from '@/shared/components/page'

/**
 * Recommendations -- the complete operational decision and action
 * lifecycle. Recommendations are discovered inside the Dashboard and
 * Investigations; this workspace owns everything that happens to one
 * from that point forward: review, approval, rejection, implementation
 * status, monitoring, and completed actions. Per the approved workspace
 * refinement, this absorbed the standalone Action Center workspace's
 * decision-and-action responsibility -- Action Center no longer exists
 * as a separate workspace. Architectural structure only; every section
 * below is wired to real operational data in a future step.
 */
export function RecommendationsWorkspace() {
  return (
    <WorkspaceContainer
      title="Recommendations"
      description="The complete recommendation decision and action lifecycle -- review, approval, implementation, and outcome."
    >
      <Stack gap={8}>
        <SectionContainer title="Recommendation queue" description="Open, in-progress, and historical recommendations across every incident.">
          <Grid minColumnWidth={240}>
            <PlaceholderCard title="Open recommendations" />
            <PlaceholderCard title="Recommendation history" />
            <PlaceholderCard title="Status overview" />
          </Grid>
        </SectionContainer>

        <SectionContainer title="Decision & action" description="Review, approve, reject, and track recommendations through to completion.">
          <Grid minColumnWidth={240}>
            <PlaceholderCard title="Pending review" />
            <PlaceholderCard title="Approvals & rejections" />
            <PlaceholderCard title="Implementation status" />
            <PlaceholderCard title="Completed actions" />
          </Grid>
        </SectionContainer>
      </Stack>
    </WorkspaceContainer>
  )
}
