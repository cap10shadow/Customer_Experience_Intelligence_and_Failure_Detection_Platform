import { Link } from 'react-router-dom'

import { ROUTE_PATHS } from '@/app/routing/routePaths'
import { Panel, Stack } from '@/shared/components/layout'
import { Icon } from '@/shared/icons'

import { InvestigationLoadingState } from '../foundation'
import type { RecommendedAction } from '../../types'
import styles from './RecommendationSummary.module.css'

export interface RecommendationSummaryProps {
  action: RecommendedAction
  isLoading?: boolean
}

/**
 * Summarizes the recommended action and transitions into Recommendations
 * -- it never owns approval, implementation, or monitoring (that
 * boundary is FE-001). When a recommendation already exists for this
 * Incident, its id is carried as a query parameter so the link is
 * future-deep-link-ready: the architecture already supports opening
 * Recommendations pre-scoped to this Incident's recommendation, per the
 * Step 3 Architecture Review (item 4). Recommendations does not read
 * this parameter yet -- that wiring is explicitly out of scope here.
 */
export function RecommendationSummary({ action, isLoading = false }: RecommendationSummaryProps) {
  if (isLoading) {
    return (
      <Panel>
        <InvestigationLoadingState label="Loading recommended next step" />
      </Panel>
    )
  }

  const transitionPath = action.recommendationId
    ? `${ROUTE_PATHS.recommendations}?recommendationId=${encodeURIComponent(action.recommendationId)}`
    : ROUTE_PATHS.recommendations

  return (
    <Panel>
      <Stack gap={3}>
        <p className={styles.headline}>{action.headline}</p>
        <p className={styles.reason}>{action.reason}</p>
        <Link to={transitionPath} className={styles.transition}>
          Open in Recommendations
          <Icon name="chevronRight" size={14} />
        </Link>
      </Stack>
    </Panel>
  )
}
