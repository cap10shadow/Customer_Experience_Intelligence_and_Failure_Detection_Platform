import { describe, expect, it } from 'vitest'

import { createManualRow, parseComplaintCsv, parseComplaintJson } from '@/workspaces/ingestion/utilities/parseComplaintRows'
import type { ParsedComplaintRow } from '@/workspaces/ingestion/types'

// Normalization/validation/mapping-classification are no longer performed
// client-side (Ingestion Normalization & Mapping Layer plan, requirement
// 5) -- the backend owns them entirely via `:analyze`. These utilities
// now do STRUCTURAL parsing only: no `validateRow`, no `ENUM_FIELDS`
// normalization, no `validationError`. Coverage for classification
// itself lives in ingestion_service's own test suite
// (tests/test_mapping_service.py, tests/test_api_complaint_analysis.py).

describe('parseComplaintCsv', () => {
  it('parses a header row and maps snake_case columns to camelCase fields', () => {
    const csv = 'complaint_text,customer_region\n"Payment failed at checkout",US-East'
    const result = parseComplaintCsv(csv)
    expect(result.fileError).toBeUndefined()
    expect(result.rows).toHaveLength(1)
    expect(result.rows[0].complaintText).toBe('Payment failed at checkout')
    expect(result.rows[0].customerRegion).toBe('US-East')
  })

  it('leaves enum-shaped fields exactly as typed -- no client-side casing/whitespace normalization', () => {
    const csv = 'complaint_text,source_channel\n"Payment failed at checkout",Email'
    const result = parseComplaintCsv(csv)
    expect(result.rows[0].sourceChannel).toBe('Email')
  })

  it('reports a file-level error when no complaint_text column exists', () => {
    const csv = 'customer_region\nUS-East'
    const result = parseComplaintCsv(csv)
    expect(result.rows).toHaveLength(0)
    expect(result.fileError).toContain('complaint_text')
  })

  it('reports a file-level error for an empty file', () => {
    const result = parseComplaintCsv('')
    expect(result.fileError).toBe('The file is empty.')
  })
})

describe('parseComplaintJson', () => {
  it('parses an array of complaint objects, leaving values exactly as provided', () => {
    const json = JSON.stringify([{ complaint_text: 'Delivery never arrived at destination', source_channel: 'CHAT' }])
    const result = parseComplaintJson(json)
    expect(result.fileError).toBeUndefined()
    expect(result.rows).toHaveLength(1)
    expect(result.rows[0].sourceChannel).toBe('CHAT')
  })

  it('reports a file-level error for invalid JSON', () => {
    const result = parseComplaintJson('{not valid')
    expect(result.fileError).toBe('The file is not valid JSON.')
  })

  it('reports a file-level error when the JSON root is not an array', () => {
    const result = parseComplaintJson('{}')
    expect(result.fileError).toBe('The JSON file must contain an array of complaint objects.')
  })
})

describe('createManualRow', () => {
  it('produces a row with a stable rowId and no local validation state', () => {
    const row: ParsedComplaintRow = createManualRow({ complaintText: 'Manually entered complaint text here' })
    expect(row.rowId).toBeTruthy()
    expect(row.complaintText).toBe('Manually entered complaint text here')
  })
})
