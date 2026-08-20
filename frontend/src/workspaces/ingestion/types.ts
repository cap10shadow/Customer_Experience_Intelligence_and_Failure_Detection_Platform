/**
 * Frontend-local domain types for the Data / Ingestion workspace. Field
 * names mirror ingestion_service's own `ComplaintCreateRequest` (the real
 * backend contract, see `api/types.ts`) so a parsed row maps 1:1 onto the
 * request body sent for it -- nothing here invents a field the backend
 * doesn't accept.
 */
export interface ParsedComplaintRow {
  /** Stable per-row identity for this browser session only (React keys, per-row submission tracking) -- never sent to the backend and never confused with a persisted complaint id. */
  rowId: string
  /** The name of the file this row was parsed from -- undefined for manually-added rows. Sent to the backend (`source_file_name`) and echoed back on analyze/batch results so the upload manifest stays correct without re-deriving it from `row_number`. */
  sourceFileName?: string
  /**
   * A unique id per upload EVENT, not per filename -- two uploads of a
   * file with the same name (e.g. re-uploading "Mixed_Batch_100.csv")
   * get distinct batch ids, so the upload manifest lists them as two
   * separate entries instead of silently merging their row counts.
   */
  sourceFileBatchId?: string
  complaintText: string
  externalReferenceId?: string
  complaintTitle?: string
  complaintSource?: string
  sourceChannel?: string
  customerRegion?: string
  customerSegment?: string
  customerType?: string
  productCategory?: string
  operationalArea?: string
  serviceType?: string
  eventOccurredAt?: string
}

/**
 * The backend, not the frontend, owns normalization/mapping/validation
 * (Ingestion Normalization & Mapping Layer plan, requirement 5) -- these
 * types mirror the real `:analyze` response 1:1 rather than reinventing
 * a client-side validation shape. `status` is the four-plus-one-state
 * breakdown the review UI renders: auto-normalized / suggested mapping /
 * needs user mapping / structurally invalid, plus plain "accepted".
 */
export type { RowAnalysisApiStatus as RowAnalysisStatus, RowFieldIssueApi as RowFieldIssue } from './api/types'

export type ComplaintSubmissionOutcome = 'created' | 'duplicate' | 'rejected'

export interface ComplaintSubmissionResult {
  rowNumber: number
  outcome: ComplaintSubmissionOutcome
  message: string
  /** Only set on a genuine 'created' -- the real, persisted id ingestion_service returned. */
  complaintId?: string
}

export interface RecentComplaint {
  id: string
  complaintText: string
  complaintTitle?: string
  customerRegion?: string
  operationalArea?: string
  complaintStatus: string
  processingStage: string
  insertedAt: string
}

/** Mirrors backend/shared/constants/enums/dataset.py's DatasetVersionStatus exactly. */
export type DatasetVersionStatus = 'draft' | 'ingesting' | 'processing' | 'analyzing' | 'ready' | 'failed' | 'partially_completed'

export const DATASET_VERSION_STATUS_LABEL: Record<DatasetVersionStatus, string> = {
  draft: 'Draft',
  ingesting: 'Ingesting',
  processing: 'Processing',
  analyzing: 'Analyzing',
  ready: 'Ready',
  failed: 'Failed',
  partially_completed: 'Partially completed',
}

/** Versions whose analysis pipeline is genuinely in flight -- the UI polls while a version is in one of these states. */
export const DATASET_VERSION_IN_PROGRESS_STATUSES: DatasetVersionStatus[] = ['ingesting', 'processing', 'analyzing']

export interface DatasetVersion {
  id: string
  datasetId: string
  versionNumber: number
  status: DatasetVersionStatus
  cumulativeRecordCount: number
  newRecordCount: number
  analysisStartedAt?: string
  analysisCompletedAt?: string
  failureReason?: string
  insertedAt: string
}

export interface DatasetSummary {
  id: string
  name: string
  description?: string
  insertedAt: string
  isLegacy?: boolean
  currentVersion?: DatasetVersion
  latestVersion?: DatasetVersion
  openIncidentCount?: number
}

export interface DatasetDetail {
  id: string
  name: string
  description?: string
  insertedAt: string
  isLegacy?: boolean
  versions: DatasetVersion[]
  currentVersion?: DatasetVersion
  latestVersion?: DatasetVersion
}

/** Mirrors backend/shared/constants/enums/enrichment.py's ProcessingStage exactly. Falls back to the raw string for any value not yet mapped, so an unrecognized state is never hidden. */
export const PROCESSING_STAGE_LABEL: Record<string, string> = {
  raw_ingestion: 'Ingested',
  preprocessing: 'Preprocessing',
  enrichment: 'Enriching',
  anomaly_analysis: 'Analyzing',
  business_evaluation: 'Evaluating impact',
  recommendation_generation: 'Generating recommendations',
  completed: 'Analysis complete',
}

/** Mirrors backend/shared/constants/enums/complaint.py's ComplaintStatus exactly. Falls back to the raw string for any value not yet mapped. */
export const COMPLAINT_STATUS_LABEL: Record<string, string> = {
  pending: 'Pending',
  ingested: 'Ingested',
  normalized: 'Normalized',
  enriched: 'Enriched',
  analyzed: 'Analyzed',
  correlated: 'Correlated',
  escalated: 'Escalated',
  resolved: 'Resolved',
  archived: 'Archived',
}
