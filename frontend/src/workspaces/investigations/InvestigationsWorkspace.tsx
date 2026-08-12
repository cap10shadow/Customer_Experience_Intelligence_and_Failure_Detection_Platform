import { useParams } from 'react-router-dom'

import { ErrorBoundary } from '@/shared/components/feedback'
import { WorkspaceContainer } from '@/shared/components/page'

import { BusinessImpact } from './components/BusinessImpact'
import { Evidence } from './components/Evidence'
import { InvestigationSectionErrorGate } from './components/foundation'
import { InvestigationContent, InvestigationLayout } from './components/layout'
import { Observation } from './components/Observation'
import { RecommendedNextStep } from './components/RecommendedNextStep'
import { RootCauseAnalysis } from './components/RootCauseAnalysis'
import { InvestigationContextProvider } from './context'
import { useInvestigationData } from './hooks/useInvestigationData'

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
 *
 * `incidentId` comes from the canonical `/investigations/:incidentId`
 * route param -- the central correlation key carried through context,
 * the data hook, the API call, the Gateway, and back.
 */
export function InvestigationsWorkspace() {
  const { incidentId } = useParams<{ incidentId: string }>()

  return (
    <InvestigationContextProvider incidentId={incidentId ?? null}>
      <InvestigationsWorkspaceContent />
    </InvestigationContextProvider>
  )
}

/**
 * Split from InvestigationsWorkspace so `useInvestigationData()` (which
 * reads InvestigationContext via useInvestigationContext()) runs *inside*
 * the provider tree, not above it.
 *
 * One `useInvestigationData()` call fetches the whole Investigation
 * through the Gateway's single aggregated
 * `GET /api/v1/investigations/:incidentId` -- not five separate
 * requests. A fetch failure is thrown into each section's own
 * ErrorBoundary via InvestigationSectionErrorGate, so each keeps its
 * existing per-section fallback. Every ErrorBoundary is given the hook's
 * `refetch` as `onRetry` (Part 7 rectification) so "Try again" issues a
 * genuine new request rather than merely re-rendering the same
 * already-failed state.
 */
function InvestigationsWorkspaceContent() {
  const { data, isLoading, error, refetch } = useInvestigationData()

  return (
    <WorkspaceContainer
      title="Investigations"
      description="The structured investigation of an operational incident -- evidence-driven analysis from observation through to a recommended next step."
    >
      <InvestigationLayout>
        <InvestigationContent>
          <ErrorBoundary boundaryLabel="the Observation" onRetry={refetch} resetKeys={[isLoading]}>
            <InvestigationSectionErrorGate error={error}>
              <Observation
                headline={data?.observation.headline}
                description={data?.observation.description}
                isLoading={isLoading}
              />
            </InvestigationSectionErrorGate>
          </ErrorBoundary>

          <ErrorBoundary boundaryLabel="the Evidence" onRetry={refetch} resetKeys={[isLoading]}>
            <InvestigationSectionErrorGate error={error}>
              <Evidence items={data?.evidence} isLoading={isLoading} />
            </InvestigationSectionErrorGate>
          </ErrorBoundary>

          <ErrorBoundary boundaryLabel="the Root Cause Analysis" onRetry={refetch} resetKeys={[isLoading]}>
            <InvestigationSectionErrorGate error={error}>
              <RootCauseAnalysis explanation={data?.rootCause} isLoading={isLoading} />
            </InvestigationSectionErrorGate>
          </ErrorBoundary>

          <ErrorBoundary boundaryLabel="the Business Impact" onRetry={refetch} resetKeys={[isLoading]}>
            <InvestigationSectionErrorGate error={error}>
              <BusinessImpact
                summaries={data?.businessImpact}
                confidenceLevel={data?.businessImpactConfidenceLevel}
                isLoading={isLoading}
              />
            </InvestigationSectionErrorGate>
          </ErrorBoundary>

          <ErrorBoundary boundaryLabel="the Recommended Next Step" onRetry={refetch} resetKeys={[isLoading]}>
            <InvestigationSectionErrorGate error={error}>
              <RecommendedNextStep action={data?.recommendedNextStep} isLoading={isLoading} />
            </InvestigationSectionErrorGate>
          </ErrorBoundary>
        </InvestigationContent>
      </InvestigationLayout>
    </WorkspaceContainer>
  )
}
