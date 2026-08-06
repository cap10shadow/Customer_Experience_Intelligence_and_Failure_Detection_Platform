import { Grid, SectionContainer } from '@/shared/components/layout'
import { PlaceholderCard } from '@/shared/components/feedback'
import { WorkspaceContainer } from '@/shared/components/page'

/**
 * Analytics -- historical and strategic operational intelligence.
 * Supports understanding; it does not replace the operational workflows
 * Dashboard/Investigations/Recommendations own.
 */
export function AnalyticsWorkspace() {
  return (
    <WorkspaceContainer
      title="Analytics"
      description="Historical trends, KPIs, forecasting, and regional intelligence."
    >
      <SectionContainer title="Strategic intelligence">
        <Grid minColumnWidth={240}>
          <PlaceholderCard title="Historical trends" />
          <PlaceholderCard title="Key performance indicators" />
          <PlaceholderCard title="Forecasting" />
          <PlaceholderCard title="Regional intelligence" />
        </Grid>
      </SectionContainer>
    </WorkspaceContainer>
  )
}
