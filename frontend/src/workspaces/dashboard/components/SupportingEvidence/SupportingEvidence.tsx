import { Grid } from '@/shared/components/layout'

import { DashboardEmptyState, DashboardSection } from '../foundation'
import { useDashboardContext, DASHBOARD_TIME_RANGE_LABELS } from '../../context'
import type { EvidenceItem } from '../../types'
import { EvidenceSection } from './EvidenceSection'

/**
 * Shape-only default -- never rendered as visible text. `isLoading` is
 * always passed by DashboardWorkspace once mounted, so real skeletons
 * (not this array's copy) are what a user ever sees; this exists solely
 * so a standalone render (e.g. before the first fetch resolves, or in
 * isolated component tests) has a sensible number of skeleton rows.
 */
const LOADING_SHAPE_ITEMS: EvidenceItem[] = [
  { id: 'loading-1', headline: 'supporting evidence', description: '' },
  { id: 'loading-2', headline: 'supporting evidence', description: '' },
  { id: 'loading-3', headline: 'supporting evidence', description: '' },
  { id: 'loading-4', headline: 'supporting evidence', description: '' },
]

export interface SupportingEvidenceProps {
  /** Real, factual trend summaries from anomaly_service (Step 7.X A-01) -- undefined only before the workspace's first fetch resolves. */
  items?: EvidenceItem[]
  isLoading?: boolean
}

/**
 * Confidence Building: exists to support conclusions already presented
 * in the Brief, the Decisions, and the Stories above -- never the first
 * place a user is asked to form an opinion. Insight → Story → Evidence,
 * never Charts → Interpretation. Every item is a factual count/total/
 * average sourced from anomaly_service's existing trend endpoints --
 * never a ranking, comparison, or severity claim (A-01 narrative rule).
 */
export function SupportingEvidence({ items, isLoading = false }: SupportingEvidenceProps) {
  const { timeRange } = useDashboardContext()
  const timeRangeLabel = DASHBOARD_TIME_RANGE_LABELS[timeRange]
  const resolvedItems = items ?? LOADING_SHAPE_ITEMS

  return (
    <DashboardSection
      title="Supporting evidence"
      insight={`Analytical context for the situation above, reflecting ${timeRangeLabel}.`}
      whyItMatters="Evidence increases confidence in the conclusions above; it does not replace them."
    >
      {!isLoading && resolvedItems.length === 0 ? (
        <DashboardEmptyState
          title="No supporting evidence available"
          description="Trend data could not be summarized for the selected period."
        />
      ) : (
        <Grid minColumnWidth={220}>
          {resolvedItems.map((item) => (
            <EvidenceSection key={item.id} item={item} isLoading={isLoading} />
          ))}
        </Grid>
      )}
    </DashboardSection>
  )
}
