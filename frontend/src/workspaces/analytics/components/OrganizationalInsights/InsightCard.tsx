import { classNames } from '@/shared/utilities/classNames'

import { AnalyticsLoadingState } from '../foundation'
import { useAnalyticsContext } from '../../context'
import type { OrganizationalInsight } from '../../types'
import styles from './InsightCard.module.css'

export interface InsightCardProps {
  insight: OrganizationalInsight
  isLoading?: boolean
}

/**
 * UX-006: Organizational Insights uses a distinct visual rhythm from
 * Strategic Opportunities -- a spacious, journal-like vertical list,
 * not a grid -- but the same neutral colors and typography scale as
 * every other section. Distinctness comes from spacing and grouping
 * only, never color or emphasis. Selecting an insight records it in
 * `AnalyticsContext` as the currently-referenced insight; nothing
 * downstream consumes that selection yet, the same architectural point
 * `EvidenceCard`'s selection made for Investigation.
 */
export function InsightCard({ insight, isLoading = false }: InsightCardProps) {
  const { selectedInsightId, selectInsight } = useAnalyticsContext()
  const isSelected = selectedInsightId === insight.id

  if (isLoading) {
    return (
      <div className={styles.item}>
        <AnalyticsLoadingState label="Loading organizational insight" />
      </div>
    )
  }

  return (
    <button
      type="button"
      className={classNames(styles.item, isSelected && styles.selected)}
      onClick={() => selectInsight(isSelected ? null : insight.id)}
      aria-pressed={isSelected}
    >
      <p className={styles.headline}>{insight.headline}</p>
      <p className={styles.explanation}>{insight.explanation}</p>
    </button>
  )
}
