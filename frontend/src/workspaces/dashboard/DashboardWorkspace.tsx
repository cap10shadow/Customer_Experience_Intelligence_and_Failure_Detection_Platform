import { Divider, Stack } from '@/shared/components/layout'
import { ErrorBoundary } from '@/shared/components/feedback'
import { WorkspaceContainer } from '@/shared/components/page'

import { DashboardContextProvider } from './context'
import { DecisionSummary } from './components/DecisionSummary'
import { InvestigationEntryPoints } from './components/InvestigationEntryPoints'
import { OperationalBrief } from './components/OperationalBrief'
import { SupportingEvidence } from './components/SupportingEvidence'

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
      <WorkspaceContainer
        title="Operational Intelligence Dashboard"
        description="Immediate operational awareness -- what changed, why it matters, and where to go next."
      >
        <Stack gap={10}>
          <ErrorBoundary boundaryLabel="the Operational Brief">
            <OperationalBrief />
          </ErrorBoundary>

          <Divider />

          <ErrorBoundary boundaryLabel="the Decision Summary">
            <DecisionSummary />
          </ErrorBoundary>

          <Divider />

          <ErrorBoundary boundaryLabel="the Investigation Entry Points">
            <InvestigationEntryPoints />
          </ErrorBoundary>

          <Divider />

          <ErrorBoundary boundaryLabel="the Supporting Evidence">
            <SupportingEvidence />
          </ErrorBoundary>
        </Stack>
      </WorkspaceContainer>
    </DashboardContextProvider>
  )
}
