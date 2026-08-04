import { Grid, SectionContainer } from '@/shared/components/layout'
import { PlaceholderCard } from '@/shared/components/feedback'
import { WorkspaceContainer } from '@/shared/components/page'

/**
 * Action Center -- an operational work queue, not a reporting workspace.
 * Everything here represents work someone needs to act on right now.
 * Architectural structure only; the actual queue is wired to real
 * operational data in a future step.
 */
export function ActionCenterWorkspace() {
  return (
    <WorkspaceContainer
      title="Action Center"
      description="Everything currently requiring operational attention."
    >
      <SectionContainer title="Operational queue" description="Active incidents, complaint spikes, SLA risks, and pending operational work.">
        <Grid minColumnWidth={240}>
          <PlaceholderCard title="Active incidents" />
          <PlaceholderCard title="Complaint spikes" />
          <PlaceholderCard title="SLA risks" />
          <PlaceholderCard title="Active investigations" />
        </Grid>
      </SectionContainer>
    </WorkspaceContainer>
  )
}
