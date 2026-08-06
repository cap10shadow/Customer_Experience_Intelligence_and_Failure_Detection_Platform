import { Grid, Stack } from '@/shared/components/layout'

import { ConfidencePresentation, InvestigationSection } from '../foundation'
import type { BusinessImpactDimensionSummary } from '../../types'
import { ImpactCard } from './ImpactCard'

const IMPACT_SUMMARIES: BusinessImpactDimensionSummary[] = [
  { dimension: 'financial', headline: 'Some revenue exposure', detail: 'Failed checkouts represent lost transactions while the issue is active.' },
  { dimension: 'customer', headline: 'Noticeable customer friction', detail: 'Customers attempting to pay are the ones directly affected.' },
  { dimension: 'operational', headline: 'Limited operational disruption', detail: 'Checkout is affected; other operational areas are not.' },
  { dimension: 'sla', headline: 'Approaching SLA thresholds', detail: 'Continued failures would begin to threaten related service commitments.' },
  { dimension: 'reputation', headline: 'Low reputational exposure so far', detail: 'Not yet reflected in public complaint volume.' },
]

export interface BusinessImpactProps {
  isLoading?: boolean
}

/**
 * "Why should the organization care?" -- always all five canonical
 * dimensions (Financial, Customer, Operational, SLA, Reputation),
 * matching the platform's own Business Impact Engine (BI-002/ARB-003):
 * no dimension is ever hidden or invented. One overall confidence value
 * is shown for the assessment as a whole -- it measures completeness of
 * available input data, not certainty, and must never be compared to
 * Root Cause Analysis's confidence above.
 */
export function BusinessImpact({ isLoading = false }: BusinessImpactProps) {
  return (
    <InvestigationSection id="business-impact" title="Business Impact" description="Why should the organization care?">
      <Stack gap={4}>
        <Grid minColumnWidth={200}>
          {IMPACT_SUMMARIES.map((summary) => (
            <ImpactCard key={summary.dimension} summary={summary} isLoading={isLoading} />
          ))}
        </Grid>
        {!isLoading ? <ConfidencePresentation level="high" measures="business impact data completeness" /> : null}
      </Stack>
    </InvestigationSection>
  )
}
