import { Stack } from '@/shared/components/layout'

import type { AnalyticsSeries } from '../../api'
import { AnalyticsEmptyState, AnalyticsSection } from '../foundation'
import type { TrendNarrative } from '../../types'
import { TrendNarrativeCard } from './TrendNarrativeCard'
import { TrendVisualization } from './TrendVisualization'

const DEFAULT_TRENDS: TrendNarrative[] = [
  {
    id: 'complaint-volume-trend',
    trend: 'Complaint volume has remained broadly stable across the period',
    narrative: 'No sustained increase or decrease stands out against the recent baseline.',
    evidence: 'Supported by consistent weekly complaint counts across the period.',
  },
  {
    id: 'resolution-velocity-trend',
    trend: 'Incident resolution velocity has been gradually improving',
    narrative: 'Incidents have, on average, moved from detection to resolution somewhat faster than in the prior period.',
    evidence: 'Supported by incident correlation and resolution timestamps across the period.',
  },
]

export interface TrendAnalysisProps {
  /** Defaults to illustrative content -- AnalyticsWorkspace passes real, Gateway-sourced trend narratives here instead of editing this component. */
  trends?: TrendNarrative[]
  /**
   * The real trend arrays behind those narratives, for the chart layer.
   * Optional and omitted by the illustrative default above: a chart must
   * only ever be drawn from data the backend actually returned, so a
   * component rendering example narratives draws no chart at all.
   */
  series?: AnalyticsSeries
  isLoading?: boolean
}

/**
 * "What has changed?" -- Trend → Narrative → Supporting Evidence for
 * every entry. The charts (`TrendVisualization`) are the supporting
 * evidence tier and render beneath the narratives: they support the
 * statement already made in words, never replace it, and never carry an
 * interpretation of their own.
 */
export function TrendAnalysis({ trends = DEFAULT_TRENDS, series, isLoading = false }: TrendAnalysisProps) {
  return (
    <AnalyticsSection id="trend-analysis" title="Trend Analysis" description="What has changed?">
      {!isLoading && trends.length === 0 ? (
        <AnalyticsEmptyState
          title="No trend data recorded yet"
          description="Trend analysis will appear here once complaint data has been recorded for the selected analysis period."
        />
      ) : (
        <Stack gap={4}>
          {trends.map((trend) => (
            <TrendNarrativeCard key={trend.id} trend={trend} isLoading={isLoading} />
          ))}
          <TrendVisualization series={series} isLoading={isLoading} />
        </Stack>
      )}
    </AnalyticsSection>
  )
}
