/**
 * Shapes mirroring gateway_service's `schemas/ingestion.py` DTOs exactly
 * -- the real `POST/GET /api/v1/datasets/{datasetId}/complaints`
 * contract (docs/DECISIONS.md AD-12: every complaint now belongs to a
 * real Dataset; there is no dataset-less ingestion path). Every field
 * here maps 1:1 to a real backend field; nothing is added or fabricated
 * on top of what ingestion_service itself returns.
 */
export interface IngestionComplaintApiRequest {
  complaint_text: string
  external_reference_id?: string
  complaint_title?: string
  complaint_source?: string
  source_channel?: string
  customer_region?: string
  customer_segment?: string
  customer_type?: string
  product_category?: string
  operational_area?: string
  service_type?: string
  event_occurred_at?: string
}

export interface IngestionComplaintApiResponse {
  id: string
  datasetId: string
  complaintText: string
  complaintTitle?: string | null
  externalReferenceId?: string | null
  complaintSource?: string | null
  sourceChannel?: string | null
  customerRegion?: string | null
  productCategory?: string | null
  operationalArea?: string | null
  complaintStatus: string
  processingStage: string
  insertedAt: string
}

export interface IngestionComplaintListApiResponse {
  items: IngestionComplaintApiResponse[]
  totalCount: number
  skip: number
  limit: number
}

/** Mirrors gateway_service's `schemas/dataset.py` DTOs exactly. */
export interface DatasetApiResponse {
  id: string
  name: string
  description?: string | null
  insertedAt: string
  isLegacy?: boolean
}

export type DatasetVersionApiStatus =
  | 'draft'
  | 'ingesting'
  | 'processing'
  | 'analyzing'
  | 'ready'
  | 'failed'
  | 'partially_completed'

export interface DatasetVersionApiResponse {
  id: string
  datasetId: string
  versionNumber: number
  status: DatasetVersionApiStatus
  cumulativeRecordCount: number
  newRecordCount: number
  analysisStartedAt?: string | null
  analysisCompletedAt?: string | null
  failureReason?: string | null
  insertedAt: string
}

export interface DatasetVersionListApiResponse {
  items: DatasetVersionApiResponse[]
}

export interface DatasetSummaryApiResponse {
  id: string
  name: string
  description?: string | null
  insertedAt: string
  isLegacy?: boolean
  currentVersion?: DatasetVersionApiResponse | null
  latestVersion?: DatasetVersionApiResponse | null
  openIncidentCount?: number | null
}

export interface DatasetDetailApiResponse {
  dataset: DatasetApiResponse
  versions: DatasetVersionApiResponse[]
  currentVersion?: DatasetVersionApiResponse | null
  latestVersion?: DatasetVersionApiResponse | null
}

export interface DatasetCreateApiRequest {
  name: string
  description?: string
}

/**
 * Ingestion Normalization & Mapping Layer -- :analyze/:batch/field-mappings
 * contracts. Deliberately kept snake_case (matching ingestion_service's
 * own field names) rather than remapped to camelCase like the rest of
 * this file: the Gateway forwards these payloads byte-for-byte (see
 * `ingestion_proxy.analyze_complaints`'s docstring) rather than owning a
 * parallel schema, so the frontend types the real wire contract exactly
 * as ingestion_service defines it.
 */
export interface AnalyzeRowInputApi {
  row_number: number
  complaint_text?: string
  external_reference_id?: string
  complaint_title?: string
  complaint_source?: string
  source_channel?: string
  customer_region?: string
  customer_segment?: string
  customer_type?: string
  product_category?: string
  operational_area?: string
  service_type?: string
  event_occurred_at?: string
  source_file_name?: string
}

export interface ComplaintAnalyzeApiRequest {
  analysis_session_id: string
  rows: AnalyzeRowInputApi[]
}

export type RowAnalysisApiStatus = 'accepted' | 'auto_normalized' | 'suggested_mapping' | 'needs_review' | 'rejected'
export type FieldIssueConfidence = 'high' | 'medium' | 'low'
export type FieldIssueProblem = 'needs_mapping' | 'invalid_enum' | 'invalid_format' | 'required_missing'
export type FieldIssueAction = 'accept_suggestion' | 'review_mapping' | 'fix_value' | 'provide_value'

export interface RowFieldIssueApi {
  row_number: number
  field: string
  provided_value: string
  problem: FieldIssueProblem
  confidence?: FieldIssueConfidence
  suggested_target_value?: string
  suggested_action: FieldIssueAction
}

export interface RowAnalysisResultApi {
  row_number: number
  status: RowAnalysisApiStatus
  issues: RowFieldIssueApi[]
  normalized_preview: Record<string, string>
  source_file_name?: string
}

export interface PendingClusterSummaryApi {
  field_name: string
  raw_value_normalized: string
  example_values: string[]
  occurrence_count: number
  confidence: 'medium' | 'low'
  suggested_target_value?: string
  mapping_id: string
  valid_choices?: string[]
}

export interface AnalyzeSummaryApi {
  accepted: number
  auto_normalized: number
  suggested_mapping: number
  needs_review: number
  rejected: number
}

export interface ComplaintAnalyzeApiResponse {
  dataset_id: string
  total_rows: number
  summary: AnalyzeSummaryApi
  pending_clusters: PendingClusterSummaryApi[]
  results: RowAnalysisResultApi[]
  page: number
  page_size: number
  total_pages: number
}

export interface ComplaintBatchApiRequest {
  analysis_session_id: string
  rows: AnalyzeRowInputApi[]
}

export type BatchRowApiOutcome = 'created' | 'duplicate' | 'rejected'

export interface BatchRowOutcomeApi {
  row_number: number
  outcome: BatchRowApiOutcome
  complaint_id?: string
  reason?: string
  source_file_name?: string
}

export interface ComplaintBatchApiResponse {
  dataset_id: string
  dataset_version_id: string
  total_rows: number
  created_count: number
  duplicate_count: number
  rejected_count: number
  outcomes: BatchRowOutcomeApi[]
}

export interface FieldValueMappingApi {
  id: string
  field_name: string
  raw_value_normalized: string
  raw_value_original_example: string
  target_value?: string
  suggested_target_value?: string
  confidence: 'high' | 'medium' | 'low'
  mapping_type?: 'alias' | 'canonical_self'
  status: 'pending' | 'approved' | 'rejected'
  occurrence_count: number
  reviewed_by?: string
  reviewed_at?: string
  inserted_at: string
}

export interface FieldValueMappingListApiResponse {
  items: FieldValueMappingApi[]
  total_count: number
  skip: number
  limit: number
}

export interface ApproveMappingApiRequest {
  target_value: string
  reviewed_by?: string
}

export interface BulkApproveMappingApiRequest {
  mapping_ids: string[]
  target_value: string
  reviewed_by?: string
}

export interface BulkApproveMappingApiResponse {
  approved: FieldValueMappingApi[]
}

export interface RejectMappingApiRequest {
  reviewed_by?: string
}

export interface AliasSuggestionApi {
  id: string
  field_name: string
  source_value_normalized: string
  suggested_target_value: string
  notes?: string
  created_by?: string
  inserted_at: string
}

export interface AliasSuggestionListApiResponse {
  items: AliasSuggestionApi[]
}

export interface AliasSuggestionCreateApiRequest {
  field_name: string
  source_value: string
  suggested_target_value: string
  notes?: string
  created_by?: string
}
