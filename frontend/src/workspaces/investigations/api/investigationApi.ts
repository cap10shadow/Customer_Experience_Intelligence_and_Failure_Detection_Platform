import { apiClient } from '@/app/api/client'

import type { InvestigationApiResponse } from './types'

export interface GetInvestigationOptions {
  signal?: AbortSignal
}

/**
 * The Investigation workspace's only API module -- one Gateway call per
 * Incident (per Batch 1 SS2/SS7: the Gateway aggregates; the frontend
 * never orchestrates multiple backend services itself). Never imports or
 * references any individual backend service's URL; only the centralized
 * apiClient.
 */
export function getInvestigation(incidentId: string, options: GetInvestigationOptions = {}): Promise<InvestigationApiResponse> {
  return apiClient.get<InvestigationApiResponse>(`/investigations/${encodeURIComponent(incidentId)}`, {
    signal: options.signal,
  })
}
