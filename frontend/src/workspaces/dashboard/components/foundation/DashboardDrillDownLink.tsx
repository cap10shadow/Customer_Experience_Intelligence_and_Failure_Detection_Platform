import { Link } from 'react-router-dom'

import { Icon } from '@/shared/icons'

import styles from './DashboardDrillDownLink.module.css'

export interface DashboardDrillDownLinkProps {
  to: string
  label: string
}

/**
 * The one "Drill-down" affordance every card-level component (Decision
 * Opportunity, Operational Story) ends with, per the universal
 * information hierarchy. Extracted here because both cards rendered the
 * identical link + chevron + hover treatment independently.
 */
export function DashboardDrillDownLink({ to, label }: DashboardDrillDownLinkProps) {
  return (
    <Link to={to} className={styles.drillDown}>
      {label}
      <Icon name="chevronRight" size={14} />
    </Link>
  )
}
