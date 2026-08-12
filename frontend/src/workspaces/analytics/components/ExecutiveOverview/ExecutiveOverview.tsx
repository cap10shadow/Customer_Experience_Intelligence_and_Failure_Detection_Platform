import { Grid } from '@/shared/components/layout'

import { AnalyticsEmptyState, AnalyticsSection } from '../foundation'
import type { ObservationItem, TrendNarrative } from '../../types'
import { ExecutiveOverviewCard } from './ExecutiveOverviewCard'

/** Human-readable label per real trend dimension -- presentation only, not a new calculation. */
const TREND_HEADLINE: Record<string, string> = {
  'complaint-volume-trend': 'Complaint volume',
  'category-trend': 'Complaint categories',
  'region-trend': 'Regional complaints',
  'sentiment-trend': 'Sentiment',
  'urgency-trend': 'Urgency distribution',
}

/**
 * Step 7.X A-08: builds observations directly from the already-computed
 * `trend.trend` string each TrendNarrative already carries (see
 * api/viewModel.ts's toAnalyticsViewModel) -- reused verbatim, never
 * recalculated, reworded, ranked, or compared. No sum/average/min/max/
 * change/causal language is introduced here; every word already existed
 * in the real Gateway-sourced trend data.
 */
function toObservations(trends: TrendNarrative[]): ObservationItem[] {
  return trends.map((trend) => ({
    id: trend.id,
    headline: TREND_HEADLINE[trend.id] ?? trend.id,
    detail: trend.trend,
  }))
}

export interface ExecutiveOverviewProps {
  /** Real trend narratives from the same Analytics fetch Trend Analysis uses -- undefined only before the first fetch resolves. */
  trends?: TrendNarrative[]
  isLoading?: boolean
}

/**
 * "What changed?" -- descriptive observations only. This section does
 * not evaluate performance, recommend actions, or assign meaning to
 * what it presents; it exists to state what the selected period looked
 * like, nothing more. Step 7.X A-08: every observation is a direct,
 * unmodified restatement of a real trend fact already computed for
 * Trend Analysis -- no new calculation, no ranking, no causal language.
 * An honest empty state renders when the Analytics API returns no
 * usable trend data at all, rather than falling back to illustrative
 * content.
 */
export function ExecutiveOverview({ trends, isLoading = false }: ExecutiveOverviewProps) {
  const observations = trends ? toObservations(trends) : []

  return (
    <AnalyticsSection id="executive-overview" title="Executive Overview" description="What changed?">
      {!isLoading && trends && observations.length === 0 ? (
        <AnalyticsEmptyState
          title="No observations available"
          description="Trend data could not be summarized for the selected period."
        />
      ) : (
        <Grid minColumnWidth={220}>
          {(isLoading ? PLACEHOLDER_ROWS : observations).map((observation) => (
            <ExecutiveOverviewCard key={observation.id} observation={observation} isLoading={isLoading} />
          ))}
        </Grid>
      )}
    </AnalyticsSection>
  )
}

/** Shape-only default -- never rendered as visible text; see Dashboard's SupportingEvidence LOADING_SHAPE_ITEMS precedent. */
const PLACEHOLDER_ROWS: ObservationItem[] = [
  { id: 'loading-1', headline: '', detail: '' },
  { id: 'loading-2', headline: '', detail: '' },
  { id: 'loading-3', headline: '', detail: '' },
]
