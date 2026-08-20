import { useState } from 'react'
import { Link } from 'react-router-dom'

import { ROUTE_PATHS } from '@/app/routing/routePaths'
import { Badge } from '@/shared/components/utility'
import { Panel, Stack } from '@/shared/components/layout'
import { Button, buttonClassName, DataTable, type DataTableColumn } from '@/shared/components/primitives'

import type { ComplaintSubmissionOutcome, ComplaintSubmissionResult } from '../../types'
import styles from './SubmissionResults.module.css'

export interface SubmissionResultsProps {
  results: ComplaintSubmissionResult[]
  onStartOver: () => void
}

const OUTCOME_TONE: Record<ComplaintSubmissionOutcome, 'success' | 'warning' | 'critical'> = {
  created: 'success',
  duplicate: 'warning',
  rejected: 'critical',
}

const OUTCOME_LABEL: Record<ComplaintSubmissionOutcome, string> = {
  created: 'Ingested',
  duplicate: 'Already exists',
  rejected: 'Rejected',
}

const PAGE_SIZE = 25

/**
 * The "Result" and "Next action" steps: a real per-row outcome for every
 * submitted row from the single `:batch` response (never a generic
 * "done" screen) -- `created` carries the real persisted `complaintId`,
 * `duplicate`/`rejected` carry the real reason ingestion_service
 * returned. Paginated like every other large list in this workspace;
 * always offers a real next action (Dashboard) rather than a dead end.
 */
export function SubmissionResults({ results, onStartOver }: SubmissionResultsProps) {
  const [page, setPage] = useState(1)
  const createdCount = results.filter((result) => result.outcome === 'created').length
  const duplicateCount = results.filter((result) => result.outcome === 'duplicate').length
  const rejectedCount = results.filter((result) => result.outcome === 'rejected').length

  const start = (page - 1) * PAGE_SIZE
  const pageResults = results.slice(start, start + PAGE_SIZE)

  const columns: DataTableColumn<ComplaintSubmissionResult>[] = [
    { key: 'status', header: 'Status', render: (result) => <Badge tone={OUTCOME_TONE[result.outcome]}>{OUTCOME_LABEL[result.outcome]}</Badge> },
    { key: 'row', header: 'Row', render: (result) => `#${result.rowNumber}` },
    { key: 'message', header: 'Detail', render: (result) => <span className={styles.message}>{result.message}</span> },
  ]

  return (
    <Panel>
      <Stack gap={4}>
        <div className={styles.summary}>
          <Badge tone="success">{createdCount} ingested</Badge>
          {duplicateCount > 0 ? <Badge tone="warning">{duplicateCount} already existed</Badge> : null}
          {rejectedCount > 0 ? <Badge tone="critical">{rejectedCount} rejected</Badge> : null}
        </div>

        <DataTable
          columns={columns}
          rows={pageResults}
          rowKey={(result) => String(result.rowNumber)}
          emptyTitle="No results"
          pagination={{ page, pageSize: PAGE_SIZE, totalCount: results.length, onPageChange: setPage }}
        />

        <div className={styles.actions}>
          <Button variant="secondary" onClick={onStartOver}>
            Ingest more data
          </Button>
          <Link className={buttonClassName('primary')} to={ROUTE_PATHS.dashboard}>
            View operational intelligence on the Dashboard
          </Link>
        </div>
      </Stack>
    </Panel>
  )
}
