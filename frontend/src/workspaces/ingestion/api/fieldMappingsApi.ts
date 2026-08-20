import { apiClient } from '@/app/api/client'

import type {
  AliasSuggestionCreateApiRequest,
  AliasSuggestionListApiResponse,
  ApproveMappingApiRequest,
  BulkApproveMappingApiRequest,
  BulkApproveMappingApiResponse,
  FieldValueMappingApi,
  FieldValueMappingListApiResponse,
  RejectMappingApiRequest,
} from './types'

export interface ListMappingsParams {
  fieldName: string
  confidence?: 'medium' | 'low'
  skip?: number
  limit?: number
}

/** `GET /api/v1/field-mappings/pending` -- global-per-field, not dataset-scoped (see the ingestion mapping plan's scope decision). */
export function listPendingMappings(params: ListMappingsParams): Promise<FieldValueMappingListApiResponse> {
  return apiClient.get<FieldValueMappingListApiResponse>('/v1/field-mappings/pending', {
    query: { field_name: params.fieldName, confidence: params.confidence, skip: params.skip, limit: params.limit },
  })
}

export function listApprovedMappings(params: Omit<ListMappingsParams, 'confidence'>): Promise<FieldValueMappingListApiResponse> {
  return apiClient.get<FieldValueMappingListApiResponse>('/v1/field-mappings/approved', {
    query: { field_name: params.fieldName, skip: params.skip, limit: params.limit },
  })
}

/** Approves one PENDING mapping -- "Accept" (target = the suggestion) or "Change"/"Map" (any other target) are both just this call with a different `targetValue`. */
export function approveMapping(mappingId: string, request: ApproveMappingApiRequest): Promise<FieldValueMappingApi> {
  return apiClient.post<FieldValueMappingApi>(`/v1/field-mappings/${encodeURIComponent(mappingId)}/approve`, request)
}

/** One decision resolves many rows: approves every listed mapping id to the same target in a single call. */
export function bulkApproveMappings(request: BulkApproveMappingApiRequest): Promise<BulkApproveMappingApiResponse> {
  return apiClient.post<BulkApproveMappingApiResponse>('/v1/field-mappings/bulk-approve', request)
}

export function rejectMapping(mappingId: string, request: RejectMappingApiRequest): Promise<FieldValueMappingApi> {
  return apiClient.post<FieldValueMappingApi>(`/v1/field-mappings/${encodeURIComponent(mappingId)}/reject`, request)
}

export function listAliasSuggestions(fieldName: string): Promise<AliasSuggestionListApiResponse> {
  return apiClient.get<AliasSuggestionListApiResponse>('/v1/field-mappings/alias-suggestions', {
    query: { field_name: fieldName },
  })
}

/** Curates a new registry entry -- the ONLY source of MEDIUM-confidence suggestions; never written by the classifier. */
export function createAliasSuggestion(request: AliasSuggestionCreateApiRequest) {
  return apiClient.post('/v1/field-mappings/alias-suggestions', request)
}
