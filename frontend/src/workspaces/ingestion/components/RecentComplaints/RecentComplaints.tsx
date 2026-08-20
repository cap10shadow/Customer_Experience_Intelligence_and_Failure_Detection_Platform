import { Badge } from '@/shared/components/utility'
import { DataTable, type DataTableColumn } from '@/shared/components/primitives'

import { COMPLAINT_STATUS_LABEL, PROCESSING_STAGE_LABEL, type RecentComplaint } from '../../types'

export interface RecentComplaintsProps {
  items: RecentComplaint[]
  isLoading: boolean
}

const STATUS_TONE: Record<string, 'neutral' | 'success' | 'info'> = {
  ingested: 'info',
  resolved: 'success',
}

/**
 * "View resulting intelligence" -- real, persisted complaints read back
 * through `GET /api/v1/ingestion/complaints`, so a user (or a returning
 * operator) can see what has actually entered the platform, not just
 * trust that their own last submission worked.
 */
export function RecentComplaints({ items, isLoading }: RecentComplaintsProps) {
  const columns: DataTableColumn<RecentComplaint>[] = [
    {
      key: 'status',
      header: 'Status',
      render: (row) => (
        <Badge tone={STATUS_TONE[row.complaintStatus] ?? 'neutral'}>
          {COMPLAINT_STATUS_LABEL[row.complaintStatus] ?? row.complaintStatus}
        </Badge>
      ),
    },
    { key: 'complaintText', header: 'Complaint', render: (row) => row.complaintTitle || row.complaintText },
    { key: 'customerRegion', header: 'Region', render: (row) => row.customerRegion ?? '—' },
    { key: 'operationalArea', header: 'Operational area', render: (row) => row.operationalArea ?? '—' },
    {
      key: 'processingStage',
      header: 'Processing stage',
      render: (row) => PROCESSING_STAGE_LABEL[row.processingStage] ?? row.processingStage,
    },
    { key: 'insertedAt', header: 'Ingested at', render: (row) => new Date(row.insertedAt).toLocaleString() },
  ]

  return (
    <DataTable
      columns={columns}
      rows={items}
      rowKey={(row) => row.id}
      isLoading={isLoading}
      loadingLabel="Loading recent complaints"
      emptyTitle="No complaints have been ingested yet"
      emptyDescription="Records you ingest above will appear here once the platform has persisted them."
    />
  )
}
