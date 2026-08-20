import { useMemo } from 'react'

import { Panel } from '@/shared/components/layout'

import type { ParsedComplaintRow } from '../../types'
import styles from './UploadManifest.module.css'

export interface UploadManifestProps {
  rows: ParsedComplaintRow[]
}

interface FileEntry {
  batchId: string
  fileName: string
  rowCount: number
}

/**
 * The persistent "N files · M rows" upload summary, listing every
 * uploaded file with its own row count -- previously the only way to
 * learn a multi-file upload's true total was indirectly, through a
 * validation message. Grouped by `sourceFileBatchId` (one per upload
 * EVENT), not by filename, so re-uploading a file with the same name
 * shows as its own separate entry instead of silently merging row
 * counts with a prior upload of that name. Derived entirely from the
 * live `rows` array (never a separate parallel state), so it stays
 * correct automatically as rows are removed, and is untouched by
 * analyze/batch -- neither operation mutates `rows`. Manually-added
 * rows (no `sourceFileBatchId`) are not files and are not listed here.
 */
export function UploadManifest({ rows }: UploadManifestProps) {
  const files = useMemo<FileEntry[]>(() => {
    const order: string[] = []
    const byBatch = new Map<string, FileEntry>()
    for (const row of rows) {
      if (!row.sourceFileBatchId || !row.sourceFileName) continue
      const existing = byBatch.get(row.sourceFileBatchId)
      if (existing) {
        existing.rowCount += 1
      } else {
        byBatch.set(row.sourceFileBatchId, { batchId: row.sourceFileBatchId, fileName: row.sourceFileName, rowCount: 1 })
        order.push(row.sourceFileBatchId)
      }
    }
    return order.map((batchId) => byBatch.get(batchId)!)
  }, [rows])

  if (files.length === 0) return null

  const totalRows = files.reduce((sum, file) => sum + file.rowCount, 0)

  return (
    <Panel>
      <p className={styles.heading}>
        {files.length} file{files.length === 1 ? '' : 's'} · {totalRows} row{totalRows === 1 ? '' : 's'}
      </p>
      <ul className={styles.list}>
        {files.map((file) => (
          <li key={file.batchId} className={styles.row}>
            <span className={styles.fileName}>{file.fileName}</span>
            <span className={styles.rowCount}>
              {file.rowCount} row{file.rowCount === 1 ? '' : 's'}
            </span>
          </li>
        ))}
      </ul>
    </Panel>
  )
}
