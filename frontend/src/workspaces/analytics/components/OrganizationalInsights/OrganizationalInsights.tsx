import { AnalyticsSection } from '../foundation'
import type { OrganizationalInsight } from '../../types'
import { InsightCard } from './InsightCard'

const INSIGHTS: OrganizationalInsight[] = [
  {
    id: 'provider-changes-precede-checkout-incidents',
    headline: 'Payment provider changes are a recurring precursor to checkout incidents',
    explanation: 'Across the period, checkout-related incidents have repeatedly followed provider-side changes rather than occurring independently of them. This is a supported conclusion drawn from the trend and pattern evidence above, not a new observation on its own.',
  },
]

export interface OrganizationalInsightsProps {
  isLoading?: boolean
}

/** "What has the organization learned?" -- supported conclusions only, synthesized from Trend Analysis, Pattern Discovery, and Recommendation Effectiveness above; never a bare observation and never a recommendation. */
export function OrganizationalInsights({ isLoading = false }: OrganizationalInsightsProps) {
  return (
    <AnalyticsSection id="organizational-insights" title="Organizational Insights" description="What has the organization learned?">
      <div>
        {INSIGHTS.map((insight) => (
          <InsightCard key={insight.id} insight={insight} isLoading={isLoading} />
        ))}
      </div>
    </AnalyticsSection>
  )
}
