import { apiClient } from '@/app/api/client'

import type {
  DatasetApiResponse,
  DatasetCreateApiRequest,
  DatasetDetailApiResponse,
  DatasetSummaryApiResponse,
  DatasetVersionApiResponse,
  DatasetVersionListApiResponse,
} from './types'

export interface RequestOptions {
  signal?: AbortSignal
}

/** Creates a Dataset -- the top-level analytical workspace every other dataset-aware workspace scopes itself to. */
export function createDataset(payload: DatasetCreateApiRequest, options: RequestOptions = {}): Promise<DatasetApiResponse> {
  return apiClient.post<DatasetApiResponse>('/v1/datasets', payload, { signal: options.signal })
}

/** Real per-dataset summaries (current/latest version, open incident count) -- never fabricated counts. */
export function listDatasets(options: RequestOptions = {}): Promise<DatasetSummaryApiResponse[]> {
  return apiClient.get<DatasetSummaryApiResponse[]>('/v1/datasets', { signal: options.signal })
}

export function getDataset(datasetId: string, options: RequestOptions = {}): Promise<DatasetDetailApiResponse> {
  return apiClient.get<DatasetDetailApiResponse>(`/v1/datasets/${encodeURIComponent(datasetId)}`, { signal: options.signal })
}

export function listDatasetVersions(datasetId: string, options: RequestOptions = {}): Promise<DatasetVersionListApiResponse> {
  return apiClient.get<DatasetVersionListApiResponse>(`/v1/datasets/${encodeURIComponent(datasetId)}/versions`, {
    signal: options.signal,
  })
}

export function getDatasetVersion(
  datasetId: string,
  versionId: string,
  options: RequestOptions = {},
): Promise<DatasetVersionApiResponse> {
  return apiClient.get<DatasetVersionApiResponse>(
    `/v1/datasets/${encodeURIComponent(datasetId)}/versions/${encodeURIComponent(versionId)}`,
    { signal: options.signal },
  )
}

/**
 * Closes the dataset's current draft into a real, numbered version AND
 * drives the full analysis pipeline for it (enrichment, anomaly
 * detection, incident correlation, root cause, business impact/
 * recommendations) before resolving. Synchronous on the backend -- this
 * call genuinely stays pending until the real pipeline finishes or
 * fails; callers should show real progress messaging, never a fake
 * percentage, while awaiting it (see `useDatasetVersionFinalize`).
 */
export function finalizeDatasetVersion(datasetId: string, options: RequestOptions = {}): Promise<DatasetVersionApiResponse> {
  return apiClient.post<DatasetVersionApiResponse>(
    `/v1/datasets/${encodeURIComponent(datasetId)}/versions/finalize`,
    undefined,
    { signal: options.signal },
  )
}

/**
 * Archives (soft-deletes) a dataset -- never a hard delete. Its
 * DatasetVersions, Complaints, and every downstream intelligence entity
 * stay completely intact; archiving only removes it from
 * `listDatasets`/`getDataset` by default (see backend's `is_deleted`).
 */
export function archiveDataset(datasetId: string, options: RequestOptions = {}): Promise<DatasetApiResponse> {
  return apiClient.post<DatasetApiResponse>(`/v1/datasets/${encodeURIComponent(datasetId)}/archive`, undefined, {
    signal: options.signal,
  })
}
