import { Grid } from '@/shared/components/layout'

import { AnalyticsSection } from '../foundation'
import type { ObservationItem } from '../../types'
import { ExecutiveOverviewCard } from './ExecutiveOverviewCard'

const OBSERVATIONS: ObservationItem[] = [
  { id: 'complaint-volume', headline: 'Complaint volume', detail: 'Complaint volume moved within its typical range across the selected period.' },
  { id: 'incident-count', headline: 'Incidents', detail: 'A small number of incidents were opened and correlated during the period.' },
  { id: 'recommendation-count', headline: 'Recommendations', detail: 'A small number of recommendations were generated during the period.' },
]

export interface ExecutiveOverviewProps {
  isLoading?: boolean
}

/**
 * "What changed?" -- descriptive observations only. This section does
 * not evaluate performance, recommend actions, or assign meaning to
 * what it presents; it exists to state what the selected period looked
 * like, nothing more.
 */
export function ExecutiveOverview({ isLoading = false }: ExecutiveOverviewProps) {
  return (
    <AnalyticsSection id="executive-overview" title="Executive Overview" description="What changed?">
      <Grid minColumnWidth={220}>
        {OBSERVATIONS.map((observation) => (
          <ExecutiveOverviewCard key={observation.id} observation={observation} isLoading={isLoading} />
        ))}
      </Grid>
    </AnalyticsSection>
  )
}
