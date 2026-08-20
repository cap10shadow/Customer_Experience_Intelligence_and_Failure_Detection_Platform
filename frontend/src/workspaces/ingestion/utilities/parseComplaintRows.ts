import type { ParsedComplaintRow } from '../types'

/** Recognized column/field names, both snake_case (the real backend field name) and camelCase (a friendlier header a person might type in a spreadsheet) -- never a third, invented vocabulary. */
const FIELD_ALIASES: Record<string, keyof Omit<ParsedComplaintRow, 'rowId'>> = {
  complaint_text: 'complaintText',
  complainttext: 'complaintText',
  external_reference_id: 'externalReferenceId',
  externalreferenceid: 'externalReferenceId',
  complaint_title: 'complaintTitle',
  complainttitle: 'complaintTitle',
  complaint_source: 'complaintSource',
  complaintsource: 'complaintSource',
  source_channel: 'sourceChannel',
  sourcechannel: 'sourceChannel',
  customer_region: 'customerRegion',
  customerregion: 'customerRegion',
  customer_segment: 'customerSegment',
  customersegment: 'customerSegment',
  customer_type: 'customerType',
  customertype: 'customerType',
  product_category: 'productCategory',
  productcategory: 'productCategory',
  operational_area: 'operationalArea',
  operationalarea: 'operationalArea',
  service_type: 'serviceType',
  servicetype: 'serviceType',
  event_occurred_at: 'eventOccurredAt',
  eventoccurredat: 'eventOccurredAt',
}

let rowCounter = 0
function nextRowId(): string {
  rowCounter += 1
  return `row-${Date.now()}-${rowCounter}`
}

/** Minimal RFC4180-style line splitter -- handles quoted fields containing commas/escaped quotes, the only CSV feature a real spreadsheet export is likely to use. Deliberately not a full CSV library: no dependency was installed for this (see app/api/client.ts's own "nothing requires one" convention). */
function parseCsvLines(text: string): string[][] {
  const rows: string[][] = []
  let row: string[] = []
  let field = ''
  let inQuotes = false

  for (let i = 0; i < text.length; i += 1) {
    const char = text[i]
    if (inQuotes) {
      if (char === '"') {
        if (text[i + 1] === '"') {
          field += '"'
          i += 1
        } else {
          inQuotes = false
        }
      } else {
        field += char
      }
      continue
    }

    if (char === '"') {
      inQuotes = true
    } else if (char === ',') {
      row.push(field)
      field = ''
    } else if (char === '\n' || char === '\r') {
      if (char === '\r' && text[i + 1] === '\n') i += 1
      row.push(field)
      rows.push(row)
      row = []
      field = ''
    } else {
      field += char
    }
  }
  if (field.length > 0 || row.length > 0) {
    row.push(field)
    rows.push(row)
  }

  return rows.filter((line) => line.some((cell) => cell.trim().length > 0))
}

export interface ParseResult {
  rows: ParsedComplaintRow[]
  /** File/document-level errors -- e.g. no recognizable `complaint_text` column at all. Distinct from per-row analysis results, which only exist after `:analyze` runs server-side. */
  fileError?: string
}

/**
 * Structural parsing ONLY -- no enum normalization, no validation, no
 * classification. The backend owns normalization/mapping/validation
 * (Ingestion Normalization & Mapping Layer plan, requirement 5); a
 * parsed row here is exactly what the file/form contained, sent as-is to
 * `POST .../complaints:analyze` for the real classification.
 */
export function parseComplaintCsv(text: string): ParseResult {
  const lines = parseCsvLines(text)
  if (lines.length === 0) {
    return { rows: [], fileError: 'The file is empty.' }
  }

  const header = lines[0].map((cell) => cell.trim().toLowerCase())
  const fieldForColumn = header.map((column) => FIELD_ALIASES[column])

  if (!fieldForColumn.includes('complaintText')) {
    return {
      rows: [],
      fileError:
        'No "complaint_text" column was found in the header row. Every complaint requires this field (ingestion_service\'s own required field).',
    }
  }

  const rows = lines.slice(1).map((cells) => {
    const row: ParsedComplaintRow = { rowId: nextRowId(), complaintText: '' }
    cells.forEach((rawValue, index) => {
      const field = fieldForColumn[index]
      const value = rawValue.trim()
      if (field && value) {
        ;(row as unknown as Record<string, string>)[field] = value
      }
    })
    return row
  })

  return { rows }
}

export function parseComplaintJson(text: string): ParseResult {
  let parsed: unknown
  try {
    parsed = JSON.parse(text)
  } catch {
    return { rows: [], fileError: 'The file is not valid JSON.' }
  }

  if (!Array.isArray(parsed)) {
    return { rows: [], fileError: 'The JSON file must contain an array of complaint objects.' }
  }

  const rows = parsed.map((entry) => {
    const row: ParsedComplaintRow = { rowId: nextRowId(), complaintText: '' }
    if (entry && typeof entry === 'object') {
      for (const [key, value] of Object.entries(entry as Record<string, unknown>)) {
        const field = FIELD_ALIASES[key.trim().toLowerCase()]
        if (field && typeof value === 'string' && value.trim()) {
          ;(row as unknown as Record<string, string>)[field] = value.trim()
        }
      }
    }
    return row
  })

  return { rows }
}

export function createManualRow(fields: Partial<Omit<ParsedComplaintRow, 'rowId'>>): ParsedComplaintRow {
  return { rowId: nextRowId(), complaintText: '', ...fields }
}
