import { Badge } from '@/shared/components/utility'

import type { AnalyzeSummaryApi } from '../../api'
import styles from './AnalysisSummary.module.css'

export interface AnalysisSummaryProps {
  totalRows: number
  summary: AnalyzeSummaryApi
}

/**
 * The compact, always-visible breakdown of a large upload -- shown
 * instead of ever rendering hundreds of detail rows at once (Ingestion
 * Normalization & Mapping Layer plan, requirement 4). Every count here
 * is real: `accepted`/`auto_normalized` are ready to submit as-is,
 * `suggested_mapping`/`needs_review` require a mapping decision below
 * before they'll submit, `rejected` is structurally invalid data,
 * entirely separate from the mapping tiers.
 */
export function AnalysisSummary({ totalRows, summary }: AnalysisSummaryProps) {
  return (
    <div className={styles.summary}>
      <span className={styles.total}>{totalRows} row{totalRows === 1 ? '' : 's'}</span>
      <Badge tone="success">{summary.accepted} ready</Badge>
      <Badge tone="success">{summary.auto_normalized} auto-normalized</Badge>
      {summary.suggested_mapping > 0 ? <Badge tone="info">{summary.suggested_mapping} suggested mapping</Badge> : null}
      {summary.needs_review > 0 ? <Badge tone="warning">{summary.needs_review} needs review</Badge> : null}
      {summary.rejected > 0 ? <Badge tone="critical">{summary.rejected} invalid</Badge> : null}
    </div>
  )
}
