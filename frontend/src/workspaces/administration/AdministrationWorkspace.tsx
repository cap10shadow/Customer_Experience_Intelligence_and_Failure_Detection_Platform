import { useEffect, useState } from 'react'

import { ErrorBoundary, PartialFailureNotice } from '@/shared/components/feedback'
import { WorkspaceContainer } from '@/shared/components/page'

import { AuditChangeHistory } from './components/AuditChangeHistory'
import { DataSourcesIntegrations } from './components/DataSourcesIntegrations'
import { AdministrationSectionErrorGate } from './components/foundation'
import { IntelligenceConfiguration } from './components/IntelligenceConfiguration'
import { AdministrationContent, AdministrationLayout } from './components/layout'
import { PlatformGovernance } from './components/PlatformGovernance'
import { PlatformOverview } from './components/PlatformOverview'
import { UserAccessManagement } from './components/UserAccessManagement'
import { AdministrationContextProvider } from './context'
import { useAdministrationData } from './hooks/useAdministrationData'

/**
 * Administration Workspace -- the Enterprise Control Center. Governs the
 * platform itself; it does not participate in operational intelligence
 * (no relationship to Monitor -> Understand -> Decide -> Act -> Learn).
 * Answers "How is the platform governed?" -- distinct from Dashboard
 * ("What is happening?"), Investigation ("Why did it happen?"),
 * Recommendation ("What should we do?"), and Analytics ("What have we
 * learned?").
 *
 * Reads as one page across six fixed sections (Platform Overview -> User
 * & Access Management -> Data Sources & Integrations -> Intelligence
 * Configuration -> Platform Governance -> Audit & Change History), each
 * belonging to one of three presentation registers -- State (scanned,
 * reference), Configuration (deliberate, consequence-aware), Record
 * (historical, read-only) -- expressed only as a subtle spacing rhythm
 * (ADM-005), never as grouped navigation, tabs, or a wizard.
 * `AdministrationNavigator` reuses the exact navigator family
 * Investigation, Recommendation, and Analytics already established. Each
 * section is individually error-isolated, exactly like every prior
 * Phase 10 workspace.
 *
 * The workspace owns one loading state for its initial data load and
 * passes it down to every section, matching Analytics' (Step 5)
 * established pattern -- the skeleton -> content transition each section
 * already renders (via its own `isLoading` prop) is driven by something,
 * rather than sitting unwired. Platform Overview (Step 7.X A-02) is the
 * one section with a real backend source: it additionally waits on
 * `useAdministrationData()`'s own real fetch, so its transition never
 * completes before genuine service-health data has actually arrived.
 */
const INITIAL_LOAD_DELAY_MS = 300

export function AdministrationWorkspace() {
  const [isLoading, setIsLoading] = useState(true)
  const { data, isLoading: isOverviewLoading, error: overviewError, refetch: refetchOverview } = useAdministrationData()

  useEffect(() => {
    const timeoutId = window.setTimeout(() => setIsLoading(false), INITIAL_LOAD_DELAY_MS)
    return () => window.clearTimeout(timeoutId)
  }, [])

  return (
    <AdministrationContextProvider>
      <WorkspaceContainer title="Administration" description="How is the platform governed?">
        <PartialFailureNotice warnings={data?.warnings} />
        <AdministrationLayout>
          <AdministrationContent>
            <ErrorBoundary boundaryLabel="the Platform Overview" onRetry={refetchOverview} resetKeys={[isOverviewLoading]}>
              <AdministrationSectionErrorGate error={overviewError}>
                <PlatformOverview
                  platformStatusSummary={data?.platformStatusSummary}
                  services={data?.services}
                  isLoading={isLoading || isOverviewLoading}
                />
              </AdministrationSectionErrorGate>
            </ErrorBoundary>

            <ErrorBoundary boundaryLabel="User & Access Management">
              <UserAccessManagement isLoading={isLoading} />
            </ErrorBoundary>

            <ErrorBoundary boundaryLabel="Data Sources & Integrations">
              <DataSourcesIntegrations isLoading={isLoading} />
            </ErrorBoundary>

            <ErrorBoundary boundaryLabel="the Intelligence Configuration">
              <IntelligenceConfiguration isLoading={isLoading} />
            </ErrorBoundary>

            <ErrorBoundary boundaryLabel="the Platform Governance">
              <PlatformGovernance isLoading={isLoading} />
            </ErrorBoundary>

            <ErrorBoundary boundaryLabel="the Audit & Change History">
              <AuditChangeHistory isLoading={isLoading} />
            </ErrorBoundary>
          </AdministrationContent>
        </AdministrationLayout>
      </WorkspaceContainer>
    </AdministrationContextProvider>
  )
}
