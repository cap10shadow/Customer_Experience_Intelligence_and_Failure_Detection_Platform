import { Grid } from '@/shared/components/layout'

import { DashboardSection } from '../foundation'
import { useDashboardContext, DASHBOARD_TIME_RANGE_LABELS } from '../../context'
import type { EvidenceItem } from '../../types'
import { EvidenceSection } from './EvidenceSection'

const DEFAULT_EVIDENCE_ITEMS: EvidenceItem[] = [
  { id: 'operational-trends', headline: 'Operational trends', description: 'Complaint and incident volume over time.' },
  { id: 'regional-comparison', headline: 'Regional comparison', description: 'How operational health varies across regions.' },
  { id: 'complaint-evolution', headline: 'Complaint evolution', description: 'How complaint themes shift over the selected period.' },
  { id: 'business-impact-trend', headline: 'Business impact trend', description: 'Estimated business impact over time.' },
  { id: 'sentiment-trend', headline: 'Sentiment trend', description: 'Customer sentiment trajectory over the selected period.' },
]

export interface SupportingEvidenceProps {
  /** Defaults to illustrative content -- a future step passes real evidence items here instead of editing this component. */
  items?: EvidenceItem[]
  isLoading?: boolean
}

/**
 * Confidence Building: exists to support conclusions already presented
 * in the Brief, the Decisions, and the Stories above -- never the first
 * place a user is asked to form an opinion. Insight → Story → Evidence,
 * never Charts → Interpretation.
 */
export function SupportingEvidence({ items = DEFAULT_EVIDENCE_ITEMS, isLoading = false }: SupportingEvidenceProps) {
  const { timeRange } = useDashboardContext()
  const timeRangeLabel = DASHBOARD_TIME_RANGE_LABELS[timeRange]

  return (
    <DashboardSection
      title="Supporting evidence"
      insight={`Analytical context for the situation above, reflecting ${timeRangeLabel}.`}
      whyItMatters="Evidence increases confidence in the conclusions above; it does not replace them."
    >
      <Grid minColumnWidth={220}>
        {items.map((item) => (
          <EvidenceSection key={item.id} item={item} isLoading={isLoading} />
        ))}
      </Grid>
    </DashboardSection>
  )
}
