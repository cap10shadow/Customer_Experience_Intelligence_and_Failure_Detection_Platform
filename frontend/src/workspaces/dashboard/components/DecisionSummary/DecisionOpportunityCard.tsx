import { Panel, Stack } from '@/shared/components/layout'
import { StatusIndicator } from '@/shared/components/utility'

import { DashboardDrillDownLink, DashboardLoadingState } from '../foundation'
import { IMPORTANCE_LABEL, IMPORTANCE_TONE, type DecisionOpportunity } from '../../types'
import styles from './DecisionOpportunityCard.module.css'

export interface DecisionOpportunityCardProps {
  opportunity: DecisionOpportunity
  isLoading?: boolean
}

/**
 * One Decision Opportunity, following the universal hierarchy at card
 * granularity: Headline → business Importance → Reason ("why it
 * matters") → Next Decision ("suggested next step") → optional
 * drill-down. Never a checkbox, approval button, or task-list row --
 * this step establishes what judgment is needed, not a way to act on it.
 */
export function DecisionOpportunityCard({ opportunity, isLoading = false }: DecisionOpportunityCardProps) {
  if (isLoading) {
    return (
      <Panel as="article">
        <DashboardLoadingState label="Loading decision opportunity" />
      </Panel>
    )
  }

  return (
    <Panel as="article" className={styles.card}>
      <Stack gap={2}>
        <h3 className={styles.headline}>{opportunity.headline}</h3>
        <StatusIndicator tone={IMPORTANCE_TONE[opportunity.importance]} label={IMPORTANCE_LABEL[opportunity.importance]} />
        <p className={styles.reason}>{opportunity.reason}</p>
        <p className={styles.nextDecision}>
          <span className={styles.nextDecisionLabel}>Next decision: </span>
          {opportunity.nextDecision}
        </p>
        {opportunity.drillDownPath ? (
          <DashboardDrillDownLink to={opportunity.drillDownPath} label={opportunity.drillDownLabel ?? 'Review in context'} />
        ) : null}
      </Stack>
    </Panel>
  )
}
