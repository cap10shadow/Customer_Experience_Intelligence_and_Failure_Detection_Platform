import { Link } from 'react-router-dom'

import { ROUTE_PATHS } from '@/app/routing/routePaths'
import { Icon } from '@/shared/icons'

import { useRecommendationContext } from '../../context'
import styles from './TraceabilityPanel.module.css'

/**
 * Every recommendation traces back to real evidence and, ultimately, to
 * one Incident -- never an unsourced claim. This links to that Incident
 * only (via `incidentId`, the same reference `InvestigationContext`
 * uses); it never introduces a separate "investigationId," because
 * Investigation has no identity of its own -- it is the presentation of
 * the Incident this panel already points to, not a second thing in the
 * chain. Data lineage (Evidence traces to an Incident) and navigation
 * (that Incident's story is presented in the Investigation Workspace)
 * are two different things this one link deliberately keeps separate
 * rather than implying investigation-as-entity.
 */
export function TraceabilityPanel() {
  const { incidentId } = useRecommendationContext()

  return (
    <p className={styles.panel}>
      Traced from the operational evidence and root cause already established for this incident.{' '}
      <Link to={incidentId ? `${ROUTE_PATHS.investigations}?incidentId=${encodeURIComponent(incidentId)}` : ROUTE_PATHS.investigations} className={styles.link}>
        Review the full investigation
        <Icon name="chevronRight" size={14} />
      </Link>
    </p>
  )
}
