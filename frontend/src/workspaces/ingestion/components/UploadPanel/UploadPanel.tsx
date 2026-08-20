import { useId, useRef, useState, type ChangeEvent, type FormEvent } from 'react'

import { Panel, Stack } from '@/shared/components/layout'
import { Button } from '@/shared/components/primitives'
import { CUSTOMER_SEGMENTS, CUSTOMER_TYPES, SERVICE_TYPES, SOURCE_CHANNELS } from '@/shared/constants/enums'

import { createManualRow, parseComplaintCsv, parseComplaintJson } from '../../utilities/parseComplaintRows'
import type { ParsedComplaintRow } from '../../types'
import styles from './UploadPanel.module.css'

/**
 * The four fields that still only accept one of a closed list, shown for
 * reference only -- validated server-side by `:analyze`, not here.
 * `customer_region`/`operational_area` are deliberately absent: real
 * business vocabulary for those two is accepted and resolved through the
 * mapping workflow below the preview table, not a fixed list a person
 * has to already know.
 */
const ENUM_FIELD_HELP: { label: string; values: readonly string[] }[] = [
  { label: 'source_channel', values: SOURCE_CHANNELS },
  { label: 'customer_segment', values: CUSTOMER_SEGMENTS },
  { label: 'customer_type', values: CUSTOMER_TYPES },
  { label: 'service_type', values: SERVICE_TYPES },
]

export interface UploadPanelProps {
  onRowsParsed: (rows: ParsedComplaintRow[]) => void
  onManualRowAdded: (row: ParsedComplaintRow) => void
}

/**
 * The "Upload" step (master task's Data flow: Upload -> Validate ->
 * Preview -> Confirm -> Ingest). No bulk/CSV endpoint exists on the
 * backend (ingestion_service accepts one `POST /complaints` at a time),
 * so a CSV/JSON file is parsed entirely client-side into rows that are
 * later submitted one real request at a time (see
 * useComplaintSubmission) -- this panel never claims a "batch upload"
 * capability the platform doesn't have. A manual single-complaint form
 * is offered alongside file upload for a user with no file to bring.
 */
export function UploadPanel({ onRowsParsed, onManualRowAdded }: UploadPanelProps) {
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [fileError, setFileError] = useState<string | undefined>(undefined)
  const [manualText, setManualText] = useState('')
  const [manualRegion, setManualRegion] = useState('')
  const manualTextId = useId()
  const manualRegionId = useId()

  const readFile = (file: File): Promise<void> =>
    new Promise((resolve) => {
      const reader = new FileReader()
      reader.onload = () => {
        const text = typeof reader.result === 'string' ? reader.result : ''
        const result = file.name.toLowerCase().endsWith('.json') ? parseComplaintJson(text) : parseComplaintCsv(text)
        if (result.fileError) {
          setFileError(`${file.name}: ${result.fileError}`)
          resolve()
          return
        }
        if (result.rows.length === 0) {
          setFileError(`${file.name}: No complaint rows were found in this file.`)
          resolve()
          return
        }
        // A unique id per upload EVENT (not per filename) -- re-uploading a
        // file with the same name still gets its own manifest entry rather
        // than silently merging into a prior upload of that name.
        const batchId = `${file.name}-${Date.now()}-${Math.random().toString(36).slice(2)}`
        onRowsParsed(result.rows.map((row) => ({ ...row, sourceFileName: file.name, sourceFileBatchId: batchId })))
        resolve()
      }
      reader.onerror = () => {
        setFileError(`${file.name}: The file could not be read.`)
        resolve()
      }
      reader.readAsText(file)
    })

  const handleFileChange = async (event: ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files ? Array.from(event.target.files) : []
    event.target.value = ''
    if (files.length === 0) return

    setFileError(undefined)
    // Sequential, not Promise.all -- keeps manifest entries in the order the
    // user selected the files, and keeps error reporting deterministic.
    for (const file of files) {
      await readFile(file)
    }
  }

  const handleManualSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    onManualRowAdded(createManualRow({ complaintText: manualText.trim(), customerRegion: manualRegion.trim() || undefined }))
    setManualText('')
    setManualRegion('')
  }

  return (
    <Stack gap={4}>
      <Panel>
        <Stack gap={3}>
          <div>
            <p className={styles.uploadTitle}>Upload a CSV or JSON file</p>
            <p className={styles.uploadHint}>
              A header row (or JSON object keys) using field names like <code>complaint_text</code>,{' '}
              <code>customer_region</code>, <code>operational_area</code>. There is no row-count limit imposed by
              this preview -- large files are analyzed and reviewed in pages, not dumped onto one screen.
              <code>complaint_text</code> is required (minimum 10 characters); every other field is optional.
            </p>
            <details className={styles.enumHelp}>
              <summary>Accepted values for restricted fields</summary>
              <p className={styles.uploadHint}>
                These four fields only accept one of the exact values below (checked after the file is analyzed,
                not while you type). <code>customer_region</code> and <code>operational_area</code> are not on this
                list -- real-world spellings and synonyms for those two (e.g. &quot;Home Delivery&quot;,
                &quot;Courier Partner&quot;) are recognized automatically or routed to a quick mapping decision after
                analysis, rather than rejected outright.
              </p>
              <ul className={styles.enumList}>
                {ENUM_FIELD_HELP.map(({ label, values }) => (
                  <li key={label}>
                    <code>{label}</code>: {values.join(', ')}
                  </li>
                ))}
              </ul>
            </details>
          </div>
          <Button
            variant="secondary"
            onClick={() => fileInputRef.current?.click()}
          >
            Choose file
          </Button>
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept=".csv,.json,text/csv,application/json"
            className={styles.hiddenInput}
            onChange={(event) => void handleFileChange(event)}
          />
          {fileError ? (
            <p role="alert" className={styles.error}>
              {fileError}
            </p>
          ) : null}
        </Stack>
      </Panel>

      <Panel>
        <form onSubmit={handleManualSubmit}>
          <Stack gap={3}>
            <p className={styles.uploadTitle}>Or add one complaint manually</p>
            <div className={styles.field}>
              <label htmlFor={manualTextId} className={styles.label}>
                Complaint text (required, minimum 10 characters)
              </label>
              <textarea
                id={manualTextId}
                className={styles.textarea}
                rows={3}
                value={manualText}
                onChange={(event) => setManualText(event.target.value)}
              />
            </div>
            <div className={styles.field}>
              <label htmlFor={manualRegionId} className={styles.label}>
                Customer region (optional)
              </label>
              <input
                id={manualRegionId}
                type="text"
                className={styles.input}
                value={manualRegion}
                onChange={(event) => setManualRegion(event.target.value)}
              />
            </div>
            <Button type="submit" variant="primary" disabled={manualText.trim().length === 0}>
              Add to preview
            </Button>
          </Stack>
        </form>
      </Panel>
    </Stack>
  )
}
