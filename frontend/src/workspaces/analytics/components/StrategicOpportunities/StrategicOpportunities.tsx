import { Grid } from '@/shared/components/layout'

import { AnalyticsSection } from '../foundation'
import type { StrategicOpportunity } from '../../types'
import { OpportunityCard } from './OpportunityCard'

const OPPORTUNITIES: StrategicOpportunity[] = [
  {
    id: 'payment-provider-change-review-process',
    headline: 'Review how payment provider changes are communicated internally',
    rationale: 'Earlier visibility into provider-side changes could shorten the time between a change and identifying its operational impact.',
  },
  {
    id: 'checkout-monitoring-investment',
    headline: 'Consider investing in more granular checkout monitoring',
    rationale: 'Finer-grained monitoring around checkout could surface this recurring pattern earlier in future periods.',
  },
]

export interface StrategicOpportunitiesProps {
  isLoading?: boolean
}

/**
 * "Where should the organization consider investing next?" --
 * organization-level opportunities only. This section never approves
 * actions, assigns work, creates initiatives, or manages a lifecycle --
 * Recommendation Workspace remains the platform's only Decision
 * Workspace.
 */
export function StrategicOpportunities({ isLoading = false }: StrategicOpportunitiesProps) {
  return (
    <AnalyticsSection
      id="strategic-opportunities"
      title="Strategic Opportunities"
      description="Where should the organization consider investing next?"
    >
      <Grid minColumnWidth={240}>
        {OPPORTUNITIES.map((opportunity) => (
          <OpportunityCard key={opportunity.id} opportunity={opportunity} isLoading={isLoading} />
        ))}
      </Grid>
    </AnalyticsSection>
  )
}
