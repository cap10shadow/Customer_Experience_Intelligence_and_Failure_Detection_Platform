import { ErrorBoundary } from '@/shared/components/feedback'
import { WorkspaceContainer } from '@/shared/components/page'

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
  const { data, isLoading, error, refetch } = useAnalyticsData()

  return (
    <WorkspaceContainer title="Analytics" description="What has the organization learned over time?">
      <AnalyticsLayout>
        <AnalyticsContent>
          <ErrorBoundary boundaryLabel="the Executive Overview" onRetry={refetch} resetKeys={[isLoading]}>
            <AnalyticsSectionErrorGate error={error}>
              <ExecutiveOverview trends={data?.trends} isLoading={isLoading} />
            </AnalyticsSectionErrorGate>
          </ErrorBoundary>

          <ErrorBoundary boundaryLabel="the Trend Analysis" onRetry={refetch} resetKeys={[isLoading]}>
            <AnalyticsSectionErrorGate error={error}>
              <TrendAnalysis trends={data?.trends} isLoading={isLoading} />
            </AnalyticsSectionErrorGate>
          </ErrorBoundary>

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
        </AnalyticsContent>
      </AnalyticsLayout>
    </WorkspaceContainer>
  )
}
