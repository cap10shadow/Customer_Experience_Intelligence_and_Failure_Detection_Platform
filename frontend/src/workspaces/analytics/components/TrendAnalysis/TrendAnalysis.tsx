import { Stack } from '@/shared/components/layout'

import { AnalyticsEmptyState, AnalyticsSection } from '../foundation'
import type { TrendNarrative } from '../../types'
import { TrendNarrativeCard } from './TrendNarrativeCard'

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
  isLoading?: boolean
}

/** "What has changed?" -- Trend → Narrative → Supporting Evidence for every entry; charts, when they exist, will support this narrative, never replace it. */
export function TrendAnalysis({ trends = DEFAULT_TRENDS, isLoading = false }: TrendAnalysisProps) {
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
        </Stack>
      )}
    </AnalyticsSection>
  )
}
