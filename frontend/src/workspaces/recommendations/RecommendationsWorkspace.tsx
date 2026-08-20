import { useParams } from 'react-router-dom'

import { describeApiError } from '@/app/api/errors'
import { useOptionalDatasetContext } from '@/app/context/DatasetContext'
import { useOptionalAuth } from '@/auth/context/AuthContext'
import { ErrorBoundary } from '@/shared/components/feedback'
import { WorkspaceContainer } from '@/shared/components/page'

import type { RecommendationDecisionApiValue } from './api'
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
import { useRecommendationDecision } from './hooks/useRecommendationDecision'

/**
 * Recommendation Workspace -- transforms operational understanding into
 * an explainable, governed operational decision while preserving human
 * oversight. The platform recommends; humans decide. This workspace
 * represents that decision and, once it exists, the recommendation's
 * lifecycle. Read as one single-column memo (Recommendation Overview →
 * Rationale → Alternative Options → Expected Outcome → Risk Assessment →
 * Decision → Recommendation Lifecycle), with the persistent
 * `RecommendationNavigator` (reusing Investigation's navigation model)
 * keeping every section directly reachable. Decision (Step 7.X G-01) is
 * this workspace's one real write capability -- `data?.decision` is
 * `undefined` only when the backend genuinely has no decision recorded
 * for this Recommendation, never fabricated; submitting a decision
 * refetches the real, persisted state rather than optimistically
 * assuming success. Each section is individually error-isolated, exactly
 * like Dashboard and Investigation's sections, so a failure in one never
 * blanks the rest of the memo.
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
  const { isSubmitting, error: decisionError, submit } = useRecommendationDecision(recommendationId ?? null)
  // The Gateway requires `operator` for PATCH .../decision. Read here,
  // at the workspace, and passed down as a prop -- the sections
  // themselves stay presentational. `useOptionalAuth` rather than
  // `useAuth` because this workspace renders correctly with no session
  // information at all (component-level tests mount it directly); in
  // that case no role restriction is claimed, and the Gateway remains
  // the authorization boundary either way.
  const auth = useOptionalAuth()
  // AD-12 follow-up: this Recommendation's own `datasetId` (real,
  // Gateway-sourced -- see api/viewModel.ts) is never assumed to match
  // whichever dataset happens to be selected right now (a direct link or
  // an older bookmark can point at a Recommendation from a different
  // dataset than the one currently active). Shown plainly rather than
  // silently relying on the active dataset selection.
  const datasetContext = useOptionalDatasetContext()
  const datasetLabel = data
    ? `${
        data.datasetId === datasetContext?.selectedDatasetId
          ? (datasetContext.selectedDatasetName ?? data.datasetId)
          : `${data.datasetId} (not your currently selected dataset)`
      } · generated for version ${data.datasetVersionId.slice(0, 8)}`
    : undefined

  const handleSubmitDecision = (decision: RecommendationDecisionApiValue, note: string | undefined) => {
    submit(decision, note)
      .then(refetch)
      .catch(() => {
        // Real failure state is already captured in `decisionError`; nothing further to do here.
      })
  }

  return (
    <RecommendationContextProvider recommendationId={recommendationId ?? null} incidentId={data?.incidentId ?? null}>
      <WorkspaceContainer
        title="Recommendations"
        description="An explainable, governed operational decision -- the platform recommends, you decide."
        actions={datasetLabel ? <span>Dataset: {datasetLabel}</span> : undefined}
      >
        <RecommendationLayout decision={data?.decision}>
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
              <Decision
                decision={data?.decision}
                isLoading={isLoading}
                isSubmitting={isSubmitting}
                canRecordDecision={auth ? auth.hasRole('operator') : true}
                // Shared status wording (app/api/errors.ts) rather than
                // the raw envelope message -- a 403 here previously read
                // as a bare authorization string that never mentioned
                // the user's role as the reason.
                submitErrorMessage={decisionError ? describeApiError(decisionError, { subject: 'record this decision' }) : undefined}
                onSubmitDecision={recommendationId ? handleSubmitDecision : undefined}
              />
            </ErrorBoundary>

            <ErrorBoundary boundaryLabel="the Recommendation Lifecycle">
              <RecommendationLifecycle decision={data?.decision} isLoading={isLoading} />
            </ErrorBoundary>
          </RecommendationContent>
        </RecommendationLayout>
      </WorkspaceContainer>
    </RecommendationContextProvider>
  )
}
