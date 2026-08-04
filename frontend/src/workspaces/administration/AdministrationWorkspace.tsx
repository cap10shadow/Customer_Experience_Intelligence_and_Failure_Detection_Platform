import { Grid, SectionContainer } from '@/shared/components/layout'
import { PlaceholderCard } from '@/shared/components/feedback'
import { WorkspaceContainer } from '@/shared/components/page'

/**
 * Administration -- platform configuration, deliberately isolated from
 * operational workflows (it is the one workspace with no relationship to
 * Monitor → Understand → Decide → Act → Learn).
 */
export function AdministrationWorkspace() {
  return (
    <WorkspaceContainer title="Administration" description="Platform configuration.">
      <SectionContainer title="Configuration areas">
        <Grid minColumnWidth={220}>
          <PlaceholderCard title="Organization settings" />
          <PlaceholderCard title="Users" />
          <PlaceholderCard title="Roles & permissions" />
          <PlaceholderCard title="Notification preferences" />
          <PlaceholderCard title="Integrations" />
        </Grid>
      </SectionContainer>
    </WorkspaceContainer>
  )
}
