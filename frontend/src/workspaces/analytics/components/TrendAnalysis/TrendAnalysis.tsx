import { Stack } from '@/shared/components/layout'

import { AnalyticsSection } from '../foundation'
import type { TrendNarrative } from '../../types'
import { TrendNarrativeCard } from './TrendNarrativeCard'

const TRENDS: TrendNarrative[] = [
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
  isLoading?: boolean
}

/** "What has changed?" -- Trend → Narrative → Supporting Evidence for every entry; charts, when they exist, will support this narrative, never replace it. */
export function TrendAnalysis({ isLoading = false }: TrendAnalysisProps) {
  return (
    <AnalyticsSection id="trend-analysis" title="Trend Analysis" description="What has changed?">
      <Stack gap={4}>
        {TRENDS.map((trend) => (
          <TrendNarrativeCard key={trend.id} trend={trend} isLoading={isLoading} />
        ))}
      </Stack>
    </AnalyticsSection>
  )
}
