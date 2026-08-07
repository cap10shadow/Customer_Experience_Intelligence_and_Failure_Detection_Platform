import { useEffect, useState } from 'react'

import { ErrorBoundary } from '@/shared/components/feedback'
import { WorkspaceContainer } from '@/shared/components/page'

import { AnalyticsContent, AnalyticsLayout } from './components/layout'
import { ExecutiveOverview } from './components/ExecutiveOverview'
import { OrganizationalInsights } from './components/OrganizationalInsights'
import { PatternDiscovery } from './components/PatternDiscovery'
import { RecommendationEffectiveness } from './components/RecommendationEffectiveness'
import { StrategicOpportunities } from './components/StrategicOpportunities'
import { TrendAnalysis } from './components/TrendAnalysis'
import { AnalyticsContextProvider } from './context'

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
 * The workspace owns one loading state for its initial data load and
 * passes it down to every section, so the skeleton -> content transition
 * each section already renders (via its own `isLoading` prop) is actually
 * driven by something, rather than sitting unwired.
 */
const INITIAL_LOAD_DELAY_MS = 300

export function AnalyticsWorkspace() {
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    const timeoutId = window.setTimeout(() => setIsLoading(false), INITIAL_LOAD_DELAY_MS)
    return () => window.clearTimeout(timeoutId)
  }, [])

  return (
    <AnalyticsContextProvider>
      <WorkspaceContainer
        title="Analytics"
        description="What has the organization learned over time?"
      >
        <AnalyticsLayout>
          <AnalyticsContent>
            <ErrorBoundary boundaryLabel="the Executive Overview">
              <ExecutiveOverview isLoading={isLoading} />
            </ErrorBoundary>

            <ErrorBoundary boundaryLabel="the Trend Analysis">
              <TrendAnalysis isLoading={isLoading} />
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
    </AnalyticsContextProvider>
  )
}
