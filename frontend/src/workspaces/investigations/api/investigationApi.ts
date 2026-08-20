import { apiClient } from '@/app/api/client'

import type { InvestigationApiResponse, RootCauseActionApiResponse } from './types'

export interface GetInvestigationOptions {
  signal?: AbortSignal
}

/**
 * The Investigation workspace's only read API call -- one Gateway call
 * per Incident (per Batch 1 SS2/SS7: the Gateway aggregates; the frontend
 * never orchestrates multiple backend services itself). Never imports or
 * references any individual backend service's URL; only the centralized
 * apiClient.
 */
export function getInvestigation(incidentId: string, options: GetInvestigationOptions = {}): Promise<InvestigationApiResponse> {
  return apiClient.get<InvestigationApiResponse>(`/v1/investigations/${encodeURIComponent(incidentId)}`, {
    signal: options.signal,
  })
}

/**
 * Root-cause lifecycle actions -- root_cause_service's own real
 * confirm/reject/refresh capability, previously implemented backend-side
 * with no Gateway route and no frontend surface at all. Each resolves
 * once the backend has genuinely persisted the transition; callers
 * refetch `getInvestigation` afterward rather than assuming the new
 * state locally (same convention as `useRecommendationDecision`).
 */
export function confirmRootCause(incidentId: string): Promise<RootCauseActionApiResponse> {
  return apiClient.patch<RootCauseActionApiResponse>(`/v1/investigations/${encodeURIComponent(incidentId)}/root-cause/confirm`)
}

export function rejectRootCause(incidentId: string): Promise<RootCauseActionApiResponse> {
  return apiClient.patch<RootCauseActionApiResponse>(`/v1/investigations/${encodeURIComponent(incidentId)}/root-cause/reject`)
}

export function refreshRootCause(incidentId: string): Promise<RootCauseActionApiResponse> {
  return apiClient.post<RootCauseActionApiResponse>(`/v1/investigations/${encodeURIComponent(incidentId)}/root-cause/refresh`)
}
