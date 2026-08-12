import { Grid, Stack } from '@/shared/components/layout'

import { DashboardSection } from '../foundation'
import { useDashboardContext, DASHBOARD_TIME_RANGE_LABELS } from '../../context'
import type { CriticalSituation, FocusArea, HealthIndicator, KeyChange, OperationalStateLevel } from '../../types'
import { CriticalSituations } from './CriticalSituations'
import { KeyChanges } from './KeyChanges'
import { OperationalHealthSnapshot } from './OperationalHealthSnapshot'
import { OperationalStatus } from './OperationalStatus'
import { RecommendedFocus } from './RecommendedFocus'

const DEFAULT_HEALTH_INDICATORS: HealthIndicator[] = [
  { id: 'complaint-trend', label: 'Complaint trend', level: 'stable', trend: 'steady', detail: 'No significant change' },
  { id: 'customer-sentiment', label: 'Customer sentiment', level: 'stable', trend: 'steady', detail: 'Within expected range' },
  { id: 'business-impact', label: 'Business impact', level: 'stable', trend: 'steady', detail: 'No material impact detected' },
  { id: 'operational-stability', label: 'Operational stability', level: 'stable', trend: 'steady', detail: 'Systems operating normally' },
]

const DEFAULT_LEVEL: OperationalStateLevel = 'stable'
const DEFAULT_SUMMARY = 'No critical issues detected. Customer experience remains within expected thresholds.'

export interface OperationalBriefProps {
  /** Defaults to illustrative content -- DashboardWorkspace passes real, Gateway-sourced values here instead of editing this component. */
  level?: OperationalStateLevel
  summary?: string
  healthIndicators?: HealthIndicator[]
  criticalSituations?: CriticalSituation[]
  keyChanges?: KeyChange[]
  focusAreas?: FocusArea[]
  isLoading?: boolean
}

/**
 * Situational Awareness: "what is happening, and why does it matter?"
 * Always leads with the current state, then narrows to what changed and
 * where attention is best spent -- the Dashboard's first section,
 * answered before any decision or evidence is shown.
 */
export function OperationalBrief({
  level = DEFAULT_LEVEL,
  summary = DEFAULT_SUMMARY,
  healthIndicators = DEFAULT_HEALTH_INDICATORS,
  criticalSituations,
  keyChanges,
  focusAreas,
  isLoading = false,
}: OperationalBriefProps) {
  const { timeRange } = useDashboardContext()
  const timeRangeLabel = DASHBOARD_TIME_RANGE_LABELS[timeRange]

  return (
    <DashboardSection
      title="Operational brief"
      insight={`Immediate situational awareness, reflecting ${timeRangeLabel}.`}
    >
      <Stack gap={6}>
        <OperationalStatus level={level} summary={summary} timeRangeLabel={timeRangeLabel} isLoading={isLoading} />
        <Grid minColumnWidth={280}>
          <CriticalSituations situations={criticalSituations} isLoading={isLoading} />
          <KeyChanges changes={keyChanges} isLoading={isLoading} />
        </Grid>
        <RecommendedFocus focusAreas={focusAreas} isLoading={isLoading} />
        <OperationalHealthSnapshot indicators={healthIndicators} isLoading={isLoading} />
      </Stack>
    </DashboardSection>
  )
}
