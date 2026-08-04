import { ROUTE_PATHS } from '@/app/routing/routePaths'
import { Grid } from '@/shared/components/layout'

import { DashboardEmptyState, DashboardSection } from '../foundation'
import { useDashboardContext, DASHBOARD_TIME_RANGE_LABELS } from '../../context'
import type { OperationalStory } from '../../types'
import { OperationalStoryCard } from './OperationalStoryCard'

const DEFAULT_OPERATIONAL_STORIES: OperationalStory[] = [
  {
    id: 'payment-reliability-deteriorating',
    headline: 'Payment reliability deteriorating',
    situation: 'Customers are reporting more payment failures than usual, concentrated around checkout.',
    significance: 'Payment friction directly affects conversion and erodes trust at the most critical moment of the journey.',
    direction: 'Correlate failure reports against recent payment provider or release changes.',
    context: 'Complaint volume, incident timeline, and business impact are gathered in one continuous view once you open the story.',
    drillDownPath: ROUTE_PATHS.investigations,
    drillDownLabel: 'Investigate this story',
  },
  {
    id: 'delivery-performance-recovering',
    headline: 'Delivery performance recovering',
    situation: 'A prior delivery delay pattern has been trending back toward normal over the recent period.',
    significance: 'Confirms whether the earlier remediation is holding before the investigation is closed.',
    direction: 'Validate the recovery against the original root cause and recommendation.',
    context: 'The full path from the original complaint to the recommendation already applied is preserved in the story.',
    drillDownPath: ROUTE_PATHS.investigations,
    drillDownLabel: 'Review this story',
  },
]

export interface InvestigationEntryPointsProps {
  /** Defaults to illustrative content -- a future step passes real Operational Stories here instead of editing this component. */
  stories?: OperationalStory[]
  isLoading?: boolean
}

/**
 * Guided Exploration: presents Operational Stories, not investigation
 * records. Every story is the Dashboard's narrative view of an Incident
 * lifecycle (Complaint → Incident → Root Cause → Business Impact →
 * Recommendation) -- never a table row, never a raw entity id.
 */
export function InvestigationEntryPoints({ stories = DEFAULT_OPERATIONAL_STORIES, isLoading = false }: InvestigationEntryPointsProps) {
  const { timeRange } = useDashboardContext()
  const timeRangeLabel = DASHBOARD_TIME_RANGE_LABELS[timeRange]

  return (
    <DashboardSection
      title="Investigation entry points"
      insight={`Operational stories currently unfolding, reflecting ${timeRangeLabel}.`}
      whyItMatters="Each story follows one operational event from complaint through to recommendation, so context is never lost while exploring."
    >
      {!isLoading && stories.length === 0 ? (
        <DashboardEmptyState
          title="No operational stories currently need investigation"
          description="Every recent complaint pattern has already been understood and addressed."
        />
      ) : (
        <Grid minColumnWidth={280}>
          {stories.map((story) => (
            <OperationalStoryCard key={story.id} story={story} isLoading={isLoading} />
          ))}
        </Grid>
      )}
    </DashboardSection>
  )
}
