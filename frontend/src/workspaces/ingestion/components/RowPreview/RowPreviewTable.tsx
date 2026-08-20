import { Badge, type BadgeTone } from '@/shared/components/utility'
import { DataTable, type DataTableColumn } from '@/shared/components/primitives'

import type { RowAnalysisResultApi } from '../../api'
import type { ParsedComplaintRow } from '../../types'
import styles from './RowPreviewTable.module.css'

export interface RowPreviewTableProps {
  /** The full current row set -- used only to look up display fields (`rows[result.row_number - 1]`) for whichever page of `results` is being shown. */
  rows: ParsedComplaintRow[]
  /** The CURRENT PAGE of `:analyze` results -- never the full row set. This table never renders more than one page at a time (default 25, via `pagination`). */
  results: RowAnalysisResultApi[]
  page: number
  pageSize: number
  totalRows: number
  onPageChange: (page: number) => void
  onRemoveRow: (rowId: string) => void
  isLoading?: boolean
  /** A page change or re-analyze is in flight while `results` still shows the last successful page -- see DataTablePagination.isUpdating. */
  isUpdating?: boolean
}

const STATUS_TONE: Record<RowAnalysisResultApi['status'], BadgeTone> = {
  accepted: 'success',
  auto_normalized: 'success',
  suggested_mapping: 'info',
  needs_review: 'warning',
  rejected: 'critical',
}

const STATUS_LABEL: Record<RowAnalysisResultApi['status'], string> = {
  accepted: 'Ready',
  auto_normalized: 'Auto-normalized',
  suggested_mapping: 'Suggested mapping',
  needs_review: 'Needs mapping',
  rejected: 'Invalid',
}

/**
 * The "Preview" step: one server-classified row per line, four distinct
 * states (auto-normalized / suggested mapping / needs user mapping /
 * structurally invalid) plus "Ready" for a row needing no normalization
 * at all -- never a plain binary valid/invalid, and never more than one
 * page rendered at once (Ingestion Normalization & Mapping Layer plan,
 * requirement 4).
 */
export function RowPreviewTable({ rows, results, page, pageSize, totalRows, onPageChange, onRemoveRow, isLoading, isUpdating }: RowPreviewTableProps) {
  const columns: DataTableColumn<RowAnalysisResultApi>[] = [
    {
      key: 'status',
      header: 'Status',
      render: (result) => <Badge tone={STATUS_TONE[result.status]}>{STATUS_LABEL[result.status]}</Badge>,
    },
    {
      key: 'complaintText',
      header: 'Complaint text',
      render: (result) => {
        const row = rows[result.row_number - 1]
        return (
          <span>
            <span className={styles.complaintText}>{row?.complaintText || '(empty)'}</span>
            {result.issues.length > 0 ? (
              <span className={styles.issueList}>
                {result.issues.map((issue, index) => (
                  <span key={`${issue.field}-${index}`} className={styles.issue}>
                    <strong>{issue.field}</strong>: {issueMessage(issue)}
                  </span>
                ))}
              </span>
            ) : null}
          </span>
        )
      },
    },
    {
      key: 'customerRegion',
      header: 'Region',
      render: (result) => result.normalized_preview.customer_region ?? rows[result.row_number - 1]?.customerRegion ?? '—',
    },
    {
      key: 'operationalArea',
      header: 'Operational area',
      render: (result) => result.normalized_preview.operational_area ?? rows[result.row_number - 1]?.operationalArea ?? '—',
    },
    {
      key: 'remove',
      header: '',
      align: 'end',
      render: (result) => {
        const row = rows[result.row_number - 1]
        if (!row) return null
        return (
          <button type="button" className={styles.removeButton} onClick={() => onRemoveRow(row.rowId)}>
            Remove
          </button>
        )
      },
    },
  ]

  return (
    <DataTable
      columns={columns}
      rows={results}
      rowKey={(result) => rows[result.row_number - 1]?.rowId ?? String(result.row_number)}
      isLoading={isLoading}
      loadingLabel="Analyzing rows"
      emptyTitle="No rows to preview yet"
      emptyDescription="Upload a file or add a complaint manually above."
      pagination={{ page, pageSize, totalCount: totalRows, onPageChange, isUpdating }}
    />
  )
}

function issueMessage(issue: RowAnalysisResultApi['issues'][number]): string {
  switch (issue.problem) {
    case 'needs_mapping':
      return issue.confidence === 'medium'
        ? `not in the canonical vocabulary -- suggested: ${issue.suggested_target_value ?? '(see mapping review below)'}`
        : 'not in the canonical vocabulary -- needs a mapping decision below'
    case 'invalid_enum':
      return `"${issue.provided_value}" is not a recognized value`
    case 'invalid_format':
      return `"${issue.provided_value}" is not in a valid format`
    case 'required_missing':
      return 'this field is required'
    default:
      return issue.problem
  }
}
