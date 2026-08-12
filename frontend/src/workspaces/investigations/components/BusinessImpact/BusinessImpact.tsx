import { Grid, Stack } from '@/shared/components/layout'

import { ConfidencePresentation, InvestigationEmptyState, InvestigationSection } from '../foundation'
import type { BusinessImpactDimensionSummary, ConfidenceLevel } from '../../types'
import { ImpactCard } from './ImpactCard'

const DEFAULT_IMPACT_SUMMARIES: BusinessImpactDimensionSummary[] = [
  { dimension: 'financial', headline: 'Some revenue exposure', detail: 'Failed checkouts represent lost transactions while the issue is active.' },
  { dimension: 'customer', headline: 'Noticeable customer friction', detail: 'Customers attempting to pay are the ones directly affected.' },
  { dimension: 'operational', headline: 'Limited operational disruption', detail: 'Checkout is affected; other operational areas are not.' },
  { dimension: 'sla', headline: 'Approaching SLA thresholds', detail: 'Continued failures would begin to threaten related service commitments.' },
  { dimension: 'reputation', headline: 'Low reputational exposure so far', detail: 'Not yet reflected in public complaint volume.' },
]

const DEFAULT_CONFIDENCE_LEVEL: ConfidenceLevel = 'high'

export interface BusinessImpactProps {
  /** Defaults to illustrative content -- InvestigationsWorkspace passes real, Gateway-sourced dimension summaries here instead of editing this component. An explicitly empty array means the assessment genuinely hasn't run yet -- rendered as an honest empty state, not the illustrative default. */
  summaries?: BusinessImpactDimensionSummary[]
  /**
   * ARB-008 (Confidence Remains Stage-Specific): explicit `null` means
   * business_impact_service has not itself classified a confidence level
   * for this assessment -- it never gets relabeled from the raw numeric
   * `confidence` value, and Business Impact's confidence must never
   * borrow Root Cause's classification. When `null`, ConfidencePresentation
   * simply isn't rendered, rather than falling back to the illustrative
   * default.
   */
  confidenceLevel?: ConfidenceLevel | null
  isLoading?: boolean
}

/**
 * "Why should the organization care?" -- always all five canonical
 * dimensions (Financial, Customer, Operational, SLA, Reputation),
 * matching the platform's own Business Impact Engine (BI-002/ARB-003):
 * no dimension is ever hidden or invented. One overall confidence value
 * is shown for the assessment as a whole, only when the backend actually
 * provides a stage-specific classification for it -- it measures
 * completeness of available input data, not certainty, and must never be
 * compared to Root Cause Analysis's confidence above.
 */
export function BusinessImpact({
  summaries = DEFAULT_IMPACT_SUMMARIES,
  confidenceLevel = DEFAULT_CONFIDENCE_LEVEL,
  isLoading = false,
}: BusinessImpactProps) {
  return (
    <InvestigationSection id="business-impact" title="Business Impact" description="Why should the organization care?">
      {!isLoading && summaries.length === 0 ? (
        <InvestigationEmptyState
          title="Business impact has not been assessed yet"
          description="This investigation hasn't produced a business impact assessment yet. This section updates across all five dimensions as soon as one has been completed."
        />
      ) : (
        <Stack gap={4}>
          <Grid minColumnWidth={200}>
            {summaries.map((summary) => (
              <ImpactCard key={summary.dimension} summary={summary} isLoading={isLoading} />
            ))}
          </Grid>
          {!isLoading && confidenceLevel !== null ? (
            <ConfidencePresentation level={confidenceLevel} measures="business impact data completeness" />
          ) : null}
        </Stack>
      )}
    </InvestigationSection>
  )
}
