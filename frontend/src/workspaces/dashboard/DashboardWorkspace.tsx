import { Divider, Stack } from '@/shared/components/layout'
import { ErrorBoundary } from '@/shared/components/feedback'
import { WorkspaceContainer } from '@/shared/components/page'

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
 * separate requests. A fetch failure is thrown into each of the three
 * data-backed sections' own ErrorBoundary via DashboardSectionErrorGate,
 * so each keeps its existing per-section fallback; Supporting Evidence is
 * untouched (Batch 2 SS2: no backend capability for it in Step 7), so it
 * keeps rendering its own illustrative content regardless of the fetch
 * outcome. Each data-backed section's ErrorBoundary is given the hook's
 * `refetch` as `onRetry` (Part 7 rectification), so "Try again" issues a
 * genuine new GET /api/v1/dashboard request rather than merely
 * re-rendering the same already-failed state.
 */
function DashboardWorkspaceContent() {
  const { data, isLoading, error, refetch } = useDashboardData()

  return (
    <WorkspaceContainer
      title="Operational Intelligence Dashboard"
      description="Immediate operational awareness -- what changed, why it matters, and where to go next."
    >
      <Stack gap={10}>
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

        <ErrorBoundary boundaryLabel="the Decision Summary" onRetry={refetch} resetKeys={[isLoading]}>
          <DashboardSectionErrorGate error={error}>
            <DecisionSummary opportunities={data?.decisionOpportunities} isLoading={isLoading} />
          </DashboardSectionErrorGate>
        </ErrorBoundary>

        <Divider />

        <ErrorBoundary boundaryLabel="the Investigation Entry Points" onRetry={refetch} resetKeys={[isLoading]}>
          <DashboardSectionErrorGate error={error}>
            <InvestigationEntryPoints stories={data?.operationalStories} isLoading={isLoading} />
          </DashboardSectionErrorGate>
        </ErrorBoundary>

        <Divider />

        <ErrorBoundary boundaryLabel="the Supporting Evidence">
          <SupportingEvidence />
        </ErrorBoundary>
      </Stack>
    </WorkspaceContainer>
  )
}
