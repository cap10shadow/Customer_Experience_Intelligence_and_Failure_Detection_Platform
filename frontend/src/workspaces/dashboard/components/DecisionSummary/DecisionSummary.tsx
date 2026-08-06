import { ROUTE_PATHS } from '@/app/routing/routePaths'
import { Grid } from '@/shared/components/layout'

import { DashboardEmptyState, DashboardSection } from '../foundation'
import { useDashboardContext, DASHBOARD_TIME_RANGE_LABELS } from '../../context'
import type { DecisionOpportunity } from '../../types'
import { DecisionOpportunityCard } from './DecisionOpportunityCard'

const DEFAULT_DECISION_OPPORTUNITIES: DecisionOpportunity[] = [
  {
    id: 'approve-recommendation',
    headline: 'Approve recommendation',
    importance: 'high',
    reason: 'A recommendation addressing a recurring complaint pattern is ready for review, pending your approval before it moves forward.',
    nextDecision: 'Approve, request changes, or decline the proposed response.',
    drillDownPath: ROUTE_PATHS.recommendations,
    drillDownLabel: 'Review recommendation',
  },
  {
    id: 'prioritize-investigation',
    headline: 'Prioritize investigation',
    importance: 'medium',
    reason: 'Several open investigations are competing for attention; sequencing them affects how quickly root causes are confirmed.',
    nextDecision: 'Choose which investigation the team should advance first.',
    drillDownPath: ROUTE_PATHS.investigations,
    drillDownLabel: 'Review investigations',
  },
]

export interface DecisionSummaryProps {
  /** Defaults to illustrative content -- a future step passes real Decision Opportunities here instead of editing this component. */
  opportunities?: DecisionOpportunity[]
  isLoading?: boolean
}

/**
 * Judgment Support: "where does my judgment matter most?" Deliberately
 * not a work queue or alert list -- every card here represents a
 * decision only a person can make, not routine operational monitoring
 * that requires no immediate judgment.
 */
export function DecisionSummary({ opportunities = DEFAULT_DECISION_OPPORTUNITIES, isLoading = false }: DecisionSummaryProps) {
  const { timeRange } = useDashboardContext()
  const timeRangeLabel = DASHBOARD_TIME_RANGE_LABELS[timeRange]

  return (
    <DashboardSection
      title="Decision summary"
      insight={`The judgment calls most worth your attention, reflecting ${timeRangeLabel}.`}
      whyItMatters="These are moments where your judgment -- not automation -- determines the outcome."
    >
      {!isLoading && opportunities.length === 0 ? (
        <DashboardEmptyState
          title="No decisions require attention"
          description="Every open recommendation and investigation is proceeding without needing your input right now."
        />
      ) : (
        <Grid minColumnWidth={280}>
          {opportunities.map((opportunity) => (
            <DecisionOpportunityCard key={opportunity.id} opportunity={opportunity} isLoading={isLoading} />
          ))}
        </Grid>
      )}
    </DashboardSection>
  )
}
