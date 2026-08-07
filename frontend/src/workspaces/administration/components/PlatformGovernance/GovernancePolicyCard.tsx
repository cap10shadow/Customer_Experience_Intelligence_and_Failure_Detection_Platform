import { AdministrationLoadingState } from '../foundation'
import type { GovernancePolicy } from '../../types'
import styles from './GovernancePolicyCard.module.css'

export interface GovernancePolicyCardProps {
  policy: GovernancePolicy
  isLoading?: boolean
}

/**
 * ADM-001: calm, explanatory, narrative presentation -- a plain
 * paragraph block, not a button, not selectable, not styled as an
 * editable configuration row. Deliberately non-interactive (unlike
 * Analytics' `InsightCard`): Platform Governance states what the
 * organization has committed to, it is not something an administrator
 * inspects or acts on here.
 */
export function GovernancePolicyCard({ policy, isLoading = false }: GovernancePolicyCardProps) {
  if (isLoading) {
    return (
      <div className={styles.item}>
        <AdministrationLoadingState label="Loading governance policy" />
      </div>
    )
  }

  return (
    <div className={styles.item}>
      <p className={styles.headline}>{policy.headline}</p>
      <p className={styles.statement}>{policy.statement}</p>
    </div>
  )
}
