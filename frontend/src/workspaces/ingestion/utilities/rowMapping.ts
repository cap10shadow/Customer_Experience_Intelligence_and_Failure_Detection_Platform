import type { AnalyzeRowInputApi } from '../api'
import type { ParsedComplaintRow } from '../types'

/**
 * Converts the current row set into the `:analyze`/`:batch` request
 * shape. `row_number` is always the row's 1-based position in `rows` at
 * the moment of the call -- never stored on `ParsedComplaintRow` itself,
 * so removing/reordering rows can never leave a stale number behind.
 */
export function toAnalyzeRowInputs(rows: ParsedComplaintRow[]): AnalyzeRowInputApi[] {
  return rows.map((row, index) => ({
    row_number: index + 1,
    complaint_text: row.complaintText || undefined,
    external_reference_id: row.externalReferenceId || undefined,
    complaint_title: row.complaintTitle || undefined,
    complaint_source: row.complaintSource || undefined,
    source_channel: row.sourceChannel || undefined,
    customer_region: row.customerRegion || undefined,
    customer_segment: row.customerSegment || undefined,
    customer_type: row.customerType || undefined,
    product_category: row.productCategory || undefined,
    operational_area: row.operationalArea || undefined,
    service_type: row.serviceType || undefined,
    event_occurred_at: row.eventOccurredAt || undefined,
    source_file_name: row.sourceFileName || undefined,
  }))
}
