import { useParams } from 'react-router-dom'

import { ErrorBoundary } from '@/shared/components/feedback'
import { WorkspaceContainer } from '@/shared/components/page'

import { AlternativeOptions } from './components/AlternativeOptions'
import { Decision } from './components/Decision'
import { ExpectedOutcome } from './components/ExpectedOutcome'
import { RecommendationSectionErrorGate } from './components/foundation'
import { RecommendationContent, RecommendationLayout } from './components/layout'
import { RecommendationOverview } from './components/Overview'
import { RecommendationRationale } from './components/Rationale'
import { RecommendationLifecycle } from './components/RecommendationLifecycle'
import { RiskAssessment } from './components/RiskAssessment'
import { RecommendationContextProvider } from './context'
import { useRecommendationData } from './hooks/useRecommendationData'
import type { DecisionRecord } from './types'

const DECISION: DecisionRecord = {
  status: 'pending-review',
  note: 'Awaiting review. No action has been taken yet.',
}

/**
 * Recommendation Workspace -- transforms operational understanding into
 * an explainable, governed operational decision while preserving human
 * oversight. The platform recommends; humans decide. This workspace
 * represents that decision and, once it exists, the recommendation's
 * lifecycle -- it never automates the decision itself. Read as one
 * single-column memo (Recommendation Overview → Rationale → Alternative
 * Options → Expected Outcome → Risk Assessment → Decision →
 * Recommendation Lifecycle), with the persistent `RecommendationNavigator`
 * (reusing Investigation's navigation model) keeping every section
 * directly reachable and a calm, persistent reference to the current
 * decision always visible. Each section is individually error-isolated,
 * exactly like Dashboard and Investigation's sections, so a failure in
 * one never blanks the rest of the memo.
 *
 * `recommendationId` comes from the canonical
 * `/recommendations/:recommendationId` route param -- the resource
 * identity carried through the data hook, the API call, the Gateway, and
 * back (Batch 4A SS8/SS9). `incidentId` is real traceability metadata the
 * fetched Recommendation itself carries -- never a second identity.
 */
export function RecommendationsWorkspace() {
  const { recommendationId } = useParams<{ recommendationId: string }>()
  const { data, isLoading, error, refetch } = useRecommendationData(recommendationId ?? null)

  return (
    <RecommendationContextProvider recommendationId={recommendationId ?? null} incidentId={data?.incidentId ?? null}>
      <WorkspaceContainer
        title="Recommendations"
        description="An explainable, governed operational decision -- the platform recommends, you decide."
      >
        <RecommendationLayout decision={DECISION}>
          <RecommendationContent>
            <ErrorBoundary boundaryLabel="the Recommendation Overview" onRetry={refetch} resetKeys={[isLoading]}>
              <RecommendationSectionErrorGate error={error}>
                <RecommendationOverview overview={data?.overview} isLoading={isLoading} />
              </RecommendationSectionErrorGate>
            </ErrorBoundary>

            <ErrorBoundary boundaryLabel="the Recommendation Rationale" onRetry={refetch} resetKeys={[isLoading]}>
              <RecommendationSectionErrorGate error={error}>
                <RecommendationRationale reason={data?.rationale} isLoading={isLoading} />
              </RecommendationSectionErrorGate>
            </ErrorBoundary>

            <ErrorBoundary boundaryLabel="the Alternative Options">
              <AlternativeOptions />
            </ErrorBoundary>

            <ErrorBoundary boundaryLabel="the Expected Outcome">
              <ExpectedOutcome />
            </ErrorBoundary>

            <ErrorBoundary boundaryLabel="the Risk Assessment">
              <RiskAssessment />
            </ErrorBoundary>

            <ErrorBoundary boundaryLabel="the Decision">
              <Decision decision={DECISION} />
            </ErrorBoundary>

            <ErrorBoundary boundaryLabel="the Recommendation Lifecycle">
              <RecommendationLifecycle decision={DECISION} />
            </ErrorBoundary>
          </RecommendationContent>
        </RecommendationLayout>
      </WorkspaceContainer>
    </RecommendationContextProvider>
  )
}
