import { Panel } from '@/shared/components/layout'

import { AnalyticsLoadingState } from '../foundation'
import type { StrategicOpportunity } from '../../types'
import styles from './OpportunityCard.module.css'

export interface OpportunityCardProps {
  opportunity: StrategicOpportunity
  isLoading?: boolean
}

/**
 * UX-006: a compact grid card -- deliberately different spacing and
 * grouping from `InsightCard`'s spacious vertical list, using the same
 * neutral Panel surface and typography scale. An organizational
 * opportunity, never an incident recommendation: no importance badge,
 * no decision state, no drill-down into a decision workflow. Recommendation
 * Workspace remains the only Decision Workspace (per the frozen
 * architecture) -- this card never renders anything resembling
 * `DecisionSummary`.
 */
export function OpportunityCard({ opportunity, isLoading = false }: OpportunityCardProps) {
  if (isLoading) {
    return (
      <Panel>
        <AnalyticsLoadingState label="Loading strategic opportunity" />
      </Panel>
    )
  }

  return (
    <Panel>
      <p className={styles.headline}>{opportunity.headline}</p>
      <p className={styles.rationale}>{opportunity.rationale}</p>
    </Panel>
  )
}
