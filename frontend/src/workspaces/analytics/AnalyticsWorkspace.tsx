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
 * Only Trend Analysis is backed by a genuine backend capability today
 * (Part 5: anomaly_service's real `/trends` summary, via the Gateway's
 * `GET /api/v1/analytics/trends`) -- Executive Overview, Pattern
 * Discovery, Recommendation Effectiveness, Organizational Insights, and
 * Strategic Opportunities have no backend capability whatsoever and
 * remain exactly as they were (illustrative or FutureCapabilityPlaceholder),
 * unaffected by the fetch outcome. All six still share the same
 * `isLoading`, now driven by the real fetch instead of a fixed timer, so
 * the skeleton -> content transition every section already renders stays
 * wired to something real.
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
          <ErrorBoundary boundaryLabel="the Executive Overview">
            <ExecutiveOverview isLoading={isLoading} />
          </ErrorBoundary>

          <ErrorBoundary boundaryLabel="the Trend Analysis" onRetry={refetch} resetKeys={[isLoading]}>
            <AnalyticsSectionErrorGate error={error}>
              <TrendAnalysis trends={data?.trends} isLoading={isLoading} />
            </AnalyticsSectionErrorGate>
          </ErrorBoundary>

          <ErrorBoundary boundaryLabel="the Pattern Discovery">
            <PatternDiscovery isLoading={isLoading} />
          </ErrorBoundary>

          <ErrorBoundary boundaryLabel="the Recommendation Effectiveness">
            <RecommendationEffectiveness isLoading={isLoading} />
          </ErrorBoundary>

          <ErrorBoundary boundaryLabel="the Organizational Insights">
            <OrganizationalInsights isLoading={isLoading} />
          </ErrorBoundary>

          <ErrorBoundary boundaryLabel="the Strategic Opportunities">
            <StrategicOpportunities isLoading={isLoading} />
          </ErrorBoundary>
        </AnalyticsContent>
      </AnalyticsLayout>
    </WorkspaceContainer>
  )
}
