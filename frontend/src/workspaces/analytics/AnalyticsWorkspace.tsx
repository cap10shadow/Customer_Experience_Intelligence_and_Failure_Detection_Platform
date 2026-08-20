import { Link } from 'react-router-dom'

import { ApiError } from '@/app/api/errors'
import { useDatasetContext } from '@/app/context/DatasetContext'
import { ROUTE_PATHS } from '@/app/routing/routePaths'
import { Grid } from '@/shared/components/layout'
import { EmptyState, ErrorBoundary } from '@/shared/components/feedback'
import { Button, buttonClassName } from '@/shared/components/primitives'
import { WorkspaceContainer } from '@/shared/components/page'
import { DatasetVersionLabel } from '@/shared/components/utility'
import { useDataset } from '@/workspaces/ingestion/hooks/useDataset'

import { AnalyticsContent, AnalyticsLayout } from './components/layout'
import { AnalyticsSectionErrorGate } from './components/foundation'
import { ExecutiveOverview } from './components/ExecutiveOverview'
import { OrganizationalInsights } from './components/OrganizationalInsights'
import { PatternDiscovery } from './components/PatternDiscovery'
import { RecommendationEffectiveness } from './components/RecommendationEffectiveness'
import { StrategicOpportunities } from './components/StrategicOpportunities'
import { TrendAnalysis } from './components/TrendAnalysis'
import { AnalyticsContextProvider } from './context'
import { useAnalyticsData } from './hooks/useAnalyticsData'

/**
 * Analytics Workspace -- transforms operational history into
 * organizational learning. Answers one question: "What has the
 * organization learned over time?" Dashboard owns the present, at
 * breadth; Investigation and Recommendation each own one instance, in
 * depth; Analytics owns history, at breadth -- the fourth, previously
 * unclaimed quadrant. Read as one narrative document (Executive
 * Overview → Trend Analysis → Pattern Discovery → Recommendation
 * Effectiveness → Organizational Insights → Strategic Opportunities),
 * following Evidence Before Conclusions at organizational scale: Trend
 * Analysis, Pattern Discovery, and Recommendation Effectiveness are the
 * evidence tier; Organizational Insights is the synthesized conclusion;
 * Strategic Opportunities is the resulting forward-looking priority --
 * never a decision, never owned by this workspace. `AnalyticsNavigator`
 * (reusing Investigation's and Recommendation's navigation model)
 * carries the one shared Scope Indicator (UX-005) every section reads
 * rather than restating. Each section is individually error-isolated,
 * exactly like every prior Phase 10 workspace.
 *
 * Trend Analysis additionally renders the real charts
 * (`TrendVisualization`) beneath its narratives, drawn 1:1 from the same
 * `GET /api/v1/analytics/trends` response the narratives are written
 * from -- the whole response is now used, where previously five
 * populated numeric series were reduced to a handful of sentences and
 * the rest discarded.
 *
 * Trend Analysis and, as of Step 7.X A-08, Executive Overview are both
 * backed by the same genuine backend capability (anomaly_service's real
 * `/trends` summary, via the Gateway's `GET /api/v1/analytics/trends`) --
 * Executive Overview restates already-computed real trend facts, never a
 * new calculation. Pattern Discovery, Recommendation Effectiveness,
 * Organizational Insights, and Strategic Opportunities have no backend
 * capability whatsoever and render an honest `FutureCapabilityPlaceholder`
 * (Step 7.X G-02 for the first and third; Recommendation Effectiveness
 * already did before Step 7.X). Those four have no data dependency on the
 * Analytics fetch, so they render immediately rather than sharing
 * `isLoading` with the two real sections.
 */
export function AnalyticsWorkspace() {
  return (
    <AnalyticsContextProvider>
      <AnalyticsWorkspaceContent />
    </AnalyticsContextProvider>
  )
}

/**
 * Split from AnalyticsWorkspace so `useAnalyticsData()` (which reads
 * AnalyticsContext via useAnalyticsContext()) runs *inside* the provider
 * tree, not above it -- mirrors InvestigationsWorkspace/RecommendationsWorkspace.
 */
function AnalyticsWorkspaceContent() {
  const { selectedDatasetId, selectedDatasetName, setSelectedDataset } = useDatasetContext()
  const { data, isLoading, error, refetch } = useAnalyticsData()
  // Reuses the Data workspace's own `useDataset` hook for the header's real
  // version/status badge -- same rationale as DashboardWorkspace.
  const { data: datasetDetail, error: datasetError } = useDataset(selectedDatasetId)

  if (!selectedDatasetId) {
    return (
      <WorkspaceContainer title="Analytics" description="What has the organization learned over time?">
        <EmptyState
          title="No dataset selected"
          description="Analytics shows trend history for one dataset at a time -- select an existing dataset or create a new one to see its Analytics."
          action={
            <Link className={buttonClassName('primary')} to={ROUTE_PATHS.ingestion}>
              Go to Data
            </Link>
          }
        />
      </WorkspaceContainer>
    )
  }

  // The selected dataset was archived (or otherwise no longer exists) --
  // see DashboardWorkspace's identical guard for the full rationale.
  if (datasetError instanceof ApiError && datasetError.status === 404) {
    return (
      <WorkspaceContainer title="Analytics" description="What has the organization learned over time?">
        <EmptyState
          title="This dataset is no longer available"
          description="It may have been archived or removed. Select a different dataset to continue."
          action={
            <Button variant="primary" onClick={() => setSelectedDataset(null)}>
              Change dataset
            </Button>
          }
        />
      </WorkspaceContainer>
    )
  }

  return (
    <WorkspaceContainer
      title="Analytics"
      description="What has the organization learned over time?"
      actions={<DatasetVersionLabel name={selectedDatasetName ?? selectedDatasetId} detail={datasetDetail} />}
    >
      <AnalyticsLayout>
        <AnalyticsContent>
          <ErrorBoundary boundaryLabel="the Executive Overview" onRetry={refetch} resetKeys={[isLoading]}>
            <AnalyticsSectionErrorGate error={error}>
              <ExecutiveOverview trends={data?.trends} isLoading={isLoading} />
            </AnalyticsSectionErrorGate>
          </ErrorBoundary>

          <ErrorBoundary boundaryLabel="the Trend Analysis" onRetry={refetch} resetKeys={[isLoading]}>
            <AnalyticsSectionErrorGate error={error}>
              <TrendAnalysis trends={data?.trends} series={data?.series} isLoading={isLoading} />
            </AnalyticsSectionErrorGate>
          </ErrorBoundary>

          <Grid minColumnWidth={340} gap={6}>
            <ErrorBoundary boundaryLabel="the Pattern Discovery">
              <PatternDiscovery />
            </ErrorBoundary>

            <ErrorBoundary boundaryLabel="the Recommendation Effectiveness">
              <RecommendationEffectiveness isLoading={isLoading} />
            </ErrorBoundary>

            <ErrorBoundary boundaryLabel="the Organizational Insights">
              <OrganizationalInsights />
            </ErrorBoundary>

            <ErrorBoundary boundaryLabel="the Strategic Opportunities">
              <StrategicOpportunities />
            </ErrorBoundary>
          </Grid>
        </AnalyticsContent>
      </AnalyticsLayout>
    </WorkspaceContainer>
  )
}
