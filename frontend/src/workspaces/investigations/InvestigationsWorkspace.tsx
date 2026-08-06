import { ErrorBoundary } from '@/shared/components/feedback'
import { WorkspaceContainer } from '@/shared/components/page'

import { BusinessImpact } from './components/BusinessImpact'
import { Evidence } from './components/Evidence'
import { InvestigationContent, InvestigationLayout } from './components/layout'
import { Observation } from './components/Observation'
import { RecommendedNextStep } from './components/RecommendedNextStep'
import { RootCauseAnalysis } from './components/RootCauseAnalysis'
import { InvestigationContextProvider } from './context'

/**
 * Investigation Workspace -- NOT a new domain entity or a list of
 * "investigations." This workspace is the structured presentation of a
 * single Incident, the platform's existing central lifecycle object
 * (ARB-007). It exists to transform operational signals into
 * explainable operational understanding through evidence-driven
 * analysis: Observation → Evidence → Root Cause Analysis → Business
 * Impact → Recommended Next Step, read as one structured document, not
 * a wizard -- `InvestigationNavigator` stays visible throughout and
 * every section remains directly reachable. Each section is
 * individually error-isolated, exactly like the Dashboard's sections
 * (Phase 10 Step 2), so a failure in one never blanks the rest of the
 * investigation.
 */
export function InvestigationsWorkspace() {
  return (
    <InvestigationContextProvider>
      <WorkspaceContainer
        title="Investigations"
        description="The structured investigation of an operational incident -- evidence-driven analysis from observation through to a recommended next step."
      >
        <InvestigationLayout>
          <InvestigationContent>
            <ErrorBoundary boundaryLabel="the Observation">
              <Observation />
            </ErrorBoundary>

            <ErrorBoundary boundaryLabel="the Evidence">
              <Evidence />
            </ErrorBoundary>

            <ErrorBoundary boundaryLabel="the Root Cause Analysis">
              <RootCauseAnalysis />
            </ErrorBoundary>

            <ErrorBoundary boundaryLabel="the Business Impact">
              <BusinessImpact />
            </ErrorBoundary>

            <ErrorBoundary boundaryLabel="the Recommended Next Step">
              <RecommendedNextStep />
            </ErrorBoundary>
          </InvestigationContent>
        </InvestigationLayout>
      </WorkspaceContainer>
    </InvestigationContextProvider>
  )
}
