import { Link } from 'react-router-dom'

import { ApiError } from '@/app/api/errors'
import { useDatasetContext } from '@/app/context/DatasetContext'
import { ROUTE_PATHS } from '@/app/routing/routePaths'
import { Divider, Grid, Stack } from '@/shared/components/layout'
import { EmptyState, ErrorBoundary, PartialFailureNotice } from '@/shared/components/feedback'
import { Button, buttonClassName } from '@/shared/components/primitives'
import { WorkspaceContainer } from '@/shared/components/page'
import { DatasetVersionLabel } from '@/shared/components/utility'
import { useDataset } from '@/workspaces/ingestion/hooks/useDataset'

import { DashboardContextProvider } from './context'
import { DecisionSummary } from './components/DecisionSummary'
import { DashboardSectionErrorGate } from './components/foundation'
import { InvestigationEntryPoints } from './components/InvestigationEntryPoints'
import { OperationalBrief } from './components/OperationalBrief'
import { SupportingEvidence } from './components/SupportingEvidence'
import { useDashboardData } from './hooks/useDashboardData'

/**
 * Operational Intelligence Dashboard -- the application home. Not a KPI
 * dashboard: it exists to reduce the time between operational awareness
 * and confident operational action, through one continuous journey --
 * Operational Brief → Decision Summary → Investigation Entry Points →
 * Supporting Evidence -- rather than four unrelated widgets. Each
 * section is individually error-isolated, so a failure in one never
 * blanks the sections around it; all four share one Global Dashboard
 * Context so they can never disagree about scope.
 */
export function DashboardWorkspace() {
  return (
    <DashboardContextProvider>
      <DashboardWorkspaceContent />
    </DashboardContextProvider>
  )
}

/**
 * Split from DashboardWorkspace so `useDashboardData()` (which reads
 * DashboardContext via useDashboardContext()) runs *inside* the provider
 * tree, not above it.
 *
 * One `useDashboardData()` call fetches the whole Dashboard through the
 * Gateway's single aggregated `GET /api/v1/dashboard` -- not four
 * separate requests. A fetch failure is thrown into each of the four
 * data-backed sections' own ErrorBoundary via DashboardSectionErrorGate,
 * so each keeps its existing per-section fallback; Supporting Evidence
 * (Step 7.X A-01) is now real, factual trend data from the same
 * aggregated response, not illustrative content. Each data-backed
 * section's ErrorBoundary is given the hook's `refetch` as `onRetry`
 * (Part 7 rectification), so "Try again" issues a genuine new
 * GET /api/v1/dashboard request rather than merely re-rendering the
 * same already-failed state.
 */
function DashboardWorkspaceContent() {
  const { selectedDatasetId, selectedDatasetName, setSelectedDataset } = useDatasetContext()
  const { data, isLoading, error, refetch } = useDashboardData()
  // Real version/status for the header badge -- reuses the Data workspace's
  // own `useDataset` hook (GET /v1/datasets/{id}) rather than duplicating
  // fetching logic. This is a deliberate, separate call from
  // useDashboardData's aggregated fetch: showing "which finalized version
  // is this intelligence current as of" requires proof from the backend,
  // not just the dataset's name (which DatasetContext already carries
  // without a fetch).
  const { data: datasetDetail, error: datasetError } = useDataset(selectedDatasetId)

  if (!selectedDatasetId) {
    return (
      <WorkspaceContainer
        title="Operational Intelligence Dashboard"
        description="Immediate operational awareness -- what changed, why it matters, and where to go next."
      >
        <EmptyState
          title="No dataset selected"
          description="The Dashboard shows intelligence for one dataset at a time -- select an existing dataset or create a new one to see its Dashboard."
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
  // detected via this same `useDataset` fetch's own 404 (ingestion_service
  // already excludes archived datasets from GET by default), independent
  // of whether the Dashboard's own aggregated data happens to still look
  // plausible (anomaly_service/etc. have no concept of Dataset lifecycle,
  // so `useDashboardData` alone could otherwise return an
  // empty-but-plausible response for an archived dataset). Never let a
  // stale DatasetContext keep showing an archived dataset as if active.
  if (datasetError instanceof ApiError && datasetError.status === 404) {
    return (
      <WorkspaceContainer
        title="Operational Intelligence Dashboard"
        description="Immediate operational awareness -- what changed, why it matters, and where to go next."
      >
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
      title="Operational Intelligence Dashboard"
      description="Immediate operational awareness -- what changed, why it matters, and where to go next."
      actions={<DatasetVersionLabel name={selectedDatasetName ?? selectedDatasetId} detail={datasetDetail} />}
    >
      <Stack gap={10}>
        <PartialFailureNotice warnings={data?.warnings} />
        <ErrorBoundary boundaryLabel="the Operational Brief" onRetry={refetch} resetKeys={[isLoading]}>
          <DashboardSectionErrorGate error={error}>
            <OperationalBrief
              level={data?.operationalStatus.level}
              summary={data?.operationalStatus.summary}
              healthIndicators={data?.healthIndicators}
              criticalSituations={data?.criticalSituations}
              keyChanges={data?.keyChanges}
              focusAreas={data?.focusAreas}
              isLoading={isLoading}
            />
          </DashboardSectionErrorGate>
        </ErrorBoundary>

        <Divider />

        <Grid minColumnWidth={440} gap={8}>
          <ErrorBoundary boundaryLabel="the Decision Summary" onRetry={refetch} resetKeys={[isLoading]}>
            <DashboardSectionErrorGate error={error}>
              <DecisionSummary opportunities={data?.decisionOpportunities} isLoading={isLoading} />
            </DashboardSectionErrorGate>
          </ErrorBoundary>

          <ErrorBoundary boundaryLabel="the Investigation Entry Points" onRetry={refetch} resetKeys={[isLoading]}>
            <DashboardSectionErrorGate error={error}>
              <InvestigationEntryPoints stories={data?.operationalStories} isLoading={isLoading} />
            </DashboardSectionErrorGate>
          </ErrorBoundary>
        </Grid>

        <Divider />

        <ErrorBoundary boundaryLabel="the Supporting Evidence" onRetry={refetch} resetKeys={[isLoading]}>
          <DashboardSectionErrorGate error={error}>
            <SupportingEvidence items={data?.supportingEvidence} isLoading={isLoading} />
          </DashboardSectionErrorGate>
        </ErrorBoundary>
      </Stack>
    </WorkspaceContainer>
  )
}
