import type { ReactNode } from 'react'

import { EmptyState, LoadingContainer } from '@/shared/components/feedback'
import { classNames } from '@/shared/utilities/classNames'

import styles from './DataTable.module.css'

export interface DataTableColumn<TRow> {
  key: string
  header: ReactNode
  render: (row: TRow) => ReactNode
  align?: 'start' | 'end'
}

export interface DataTablePagination {
  /**
   * 1-based current page. `rows` must already be just this page's slice --
   * DataTable never re-slices. Callers must pass the page the CURRENTLY
   * RENDERED `rows` actually belong to (e.g. the server response's own
   * `page` field), never an optimistically-updated "requested page" --
   * otherwise this label and the "Showing X-Y of Z" range can advertise a
   * page whose rows never actually loaded.
   */
  page: number
  pageSize: number
  /** Total row count across every page (not just the current page's `rows.length`). */
  totalCount: number
  onPageChange: (page: number) => void
  /** A background re-fetch (new page, or a re-analyze) is in flight while `rows` still shows the last successful page -- disables Previous/Next and shows an inline indicator, distinct from `isLoading` (which replaces `rows` entirely, appropriate only for the very first load). */
  isUpdating?: boolean
}

export interface DataTableProps<TRow> {
  columns: DataTableColumn<TRow>[]
  rows: TRow[]
  /** Stable row key -- never the array index, so React reconciliation survives row insertion/removal (e.g. the Ingestion preview table removing an invalid row). */
  rowKey: (row: TRow) => string
  isLoading?: boolean
  loadingLabel?: string
  emptyTitle?: string
  emptyDescription?: string
  className?: string
  /**
   * Opt-in, controlled pagination -- omitted by every existing caller
   * (version history, recent complaints, etc.), so this changes nothing
   * for them. When present, `rows` must already be the current page's
   * slice (server-paginated or otherwise); DataTable only renders the
   * "Showing X–Y of Z" strip and Previous/Next controls, it never slices
   * `rows` itself. This is what stops the Ingestion workspace from
   * rendering hundreds of rows in one unbounded table.
   */
  pagination?: DataTablePagination
}

/**
 * The platform's one shared tabular-data primitive -- previously no
 * workspace rendered a real record-level table (every "list" was a card
 * grid). Built for the Ingestion workspace's parsed-row preview and
 * complaint list, reusing the existing `EmptyState`/`LoadingContainer`
 * primitives rather than inventing new loading/empty conventions.
 */
export function DataTable<TRow>({
  columns,
  rows,
  rowKey,
  isLoading = false,
  loadingLabel = 'Loading records',
  emptyTitle = 'No records',
  emptyDescription,
  className,
  pagination,
}: DataTableProps<TRow>) {
  return (
    <LoadingContainer isLoading={isLoading} label={loadingLabel}>
      {rows.length === 0 ? (
        <EmptyState title={emptyTitle} description={emptyDescription} />
      ) : (
        <div className={classNames(styles.wrapper, className)}>
          <table className={styles.table}>
            <thead>
              <tr>
                {columns.map((column) => (
                  <th key={column.key} className={classNames(styles.headerCell, column.align === 'end' && styles.alignEnd)}>
                    {column.header}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={rowKey(row)}>
                  {columns.map((column) => (
                    <td key={column.key} className={classNames(styles.cell, column.align === 'end' && styles.alignEnd)}>
                      {column.render(row)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
          {pagination ? <DataTablePaginationControls {...pagination} /> : null}
        </div>
      )}
    </LoadingContainer>
  )
}

function DataTablePaginationControls({ page, pageSize, totalCount, onPageChange, isUpdating = false }: DataTablePagination) {
  const totalPages = Math.max(1, Math.ceil(totalCount / pageSize))
  const rangeStart = totalCount === 0 ? 0 : (page - 1) * pageSize + 1
  const rangeEnd = Math.min(page * pageSize, totalCount)

  return (
    <div className={styles.pagination}>
      <span className={styles.paginationSummary}>
        Showing {rangeStart}–{rangeEnd} of {totalCount}
        {isUpdating ? <span className={styles.paginationUpdating}> · Updating…</span> : null}
      </span>
      <div className={styles.paginationControls}>
        <button
          type="button"
          className={styles.paginationButton}
          disabled={page <= 1 || isUpdating}
          onClick={() => onPageChange(page - 1)}
        >
          &lt; Previous
        </button>
        <span className={styles.paginationPage}>
          Page {page} of {totalPages}
        </span>
        <button
          type="button"
          className={styles.paginationButton}
          disabled={page >= totalPages || isUpdating}
          onClick={() => onPageChange(page + 1)}
        >
          Next &gt;
        </button>
      </div>
    </div>
  )
}
