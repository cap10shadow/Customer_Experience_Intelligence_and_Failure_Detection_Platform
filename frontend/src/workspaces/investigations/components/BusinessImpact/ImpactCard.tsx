import { Panel } from '@/shared/components/layout'

import { InvestigationLoadingState } from '../foundation'
import { BUSINESS_IMPACT_DIMENSION_LABEL, type BusinessImpactDimensionSummary } from '../../types'
import styles from './ImpactCard.module.css'

export interface ImpactCardProps {
  summary: BusinessImpactDimensionSummary
  isLoading?: boolean
}

/** One of the five Business Impact dimensions (BI-002 / PRD.md) -- always rendered by `BusinessImpact` as a fixed set of five, never a filtered subset. */
export function ImpactCard({ summary, isLoading = false }: ImpactCardProps) {
  if (isLoading) {
    return (
      <Panel>
        <InvestigationLoadingState label={`Loading ${BUSINESS_IMPACT_DIMENSION_LABEL[summary.dimension]} impact`} />
      </Panel>
    )
  }

  return (
    <Panel>
      <p className={styles.dimension}>{BUSINESS_IMPACT_DIMENSION_LABEL[summary.dimension]}</p>
      <p className={styles.headline}>{summary.headline}</p>
      <p className={styles.detail}>{summary.detail}</p>
    </Panel>
  )
}
