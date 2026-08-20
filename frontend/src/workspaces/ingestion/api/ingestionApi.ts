import { apiClient } from '@/app/api/client'

import type {
  ComplaintAnalyzeApiRequest,
  ComplaintAnalyzeApiResponse,
  ComplaintBatchApiRequest,
  ComplaintBatchApiResponse,
  IngestionComplaintApiRequest,
  IngestionComplaintApiResponse,
  IngestionComplaintListApiResponse,
} from './types'

export interface PostComplaintOptions {
  signal?: AbortSignal
}

/**
 * The Data workspace's write call -- one real
 * `POST /api/v1/datasets/{datasetId}/complaints` per row, through the
 * same centralized apiClient/Gateway boundary as every other workspace.
 * ingestion_service accepts one complaint per request (no bulk/CSV
 * endpoint exists); a multi-row upload calls this once per row rather
 * than fabricating a batch endpoint the backend doesn't have.
 */
export function postComplaint(
  datasetId: string,
  payload: IngestionComplaintApiRequest,
  options: PostComplaintOptions = {},
): Promise<IngestionComplaintApiResponse> {
  return apiClient.post<IngestionComplaintApiResponse>(`/v1/datasets/${encodeURIComponent(datasetId)}/complaints`, payload, {
    signal: options.signal,
  })
}

export interface ListComplaintsParams {
  skip?: number
  limit?: number
}

export interface ListComplaintsOptions {
  signal?: AbortSignal
}

/** Reads back real, persisted complaints for one dataset -- what "View resulting intelligence" actually shows after an ingest. */
export function listComplaints(
  datasetId: string,
  params: ListComplaintsParams = {},
  options: ListComplaintsOptions = {},
): Promise<IngestionComplaintListApiResponse> {
  return apiClient.get<IngestionComplaintListApiResponse>(`/v1/datasets/${encodeURIComponent(datasetId)}/complaints`, {
    query: { skip: params.skip, limit: params.limit },
    signal: options.signal,
  })
}

export interface AnalyzeComplaintsParams {
  page?: number
  pageSize?: number
}

export interface AnalyzeComplaintsOptions {
  signal?: AbortSignal
}

/**
 * `POST /api/v1/datasets/{datasetId}/complaints:analyze` -- the backend
 * classifies every row (normalization/mapping/validation) and returns a
 * paginated per-row breakdown plus a summary and pending mapping
 * clusters. Persists nothing. Safe to call repeatedly with the same
 * `analysis_session_id` (e.g. after approving a mapping) without
 * inflating mapping occurrence counts server-side.
 */
export function analyzeComplaints(
  datasetId: string,
  request: ComplaintAnalyzeApiRequest,
  params: AnalyzeComplaintsParams = {},
  options: AnalyzeComplaintsOptions = {},
): Promise<ComplaintAnalyzeApiResponse> {
  return apiClient.post<ComplaintAnalyzeApiResponse>(
    `/v1/datasets/${encodeURIComponent(datasetId)}/complaints:analyze`,
    request,
    {
      query: { page: params.page, page_size: params.pageSize },
      signal: options.signal,
    },
  )
}

export interface BatchSubmitComplaintsOptions {
  signal?: AbortSignal
}

/** `POST /api/v1/datasets/{datasetId}/complaints:batch` -- submits the same row set in one transaction, using currently-approved mappings. */
export function batchSubmitComplaints(
  datasetId: string,
  request: ComplaintBatchApiRequest,
  options: BatchSubmitComplaintsOptions = {},
): Promise<ComplaintBatchApiResponse> {
  return apiClient.post<ComplaintBatchApiResponse>(
    `/v1/datasets/${encodeURIComponent(datasetId)}/complaints:batch`,
    request,
    { signal: options.signal },
  )
}
