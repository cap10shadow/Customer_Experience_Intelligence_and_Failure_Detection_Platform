import { Link } from 'react-router-dom'

import { ROUTE_PATHS, buildRecommendationPath } from '@/app/routing/routePaths'
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
 * Incident, its id is carried via the canonical
 * `/recommendations/:recommendationId` route (Part 4) so the transition
 * opens Recommendations pre-scoped to this Incident's real recommendation.
 */
export function RecommendationSummary({ action, isLoading = false }: RecommendationSummaryProps) {
  if (isLoading) {
    return (
      <Panel>
        <InvestigationLoadingState label="Loading recommended next step" />
      </Panel>
    )
  }

  const transitionPath = action.recommendationId ? buildRecommendationPath(action.recommendationId) : ROUTE_PATHS.recommendations

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
