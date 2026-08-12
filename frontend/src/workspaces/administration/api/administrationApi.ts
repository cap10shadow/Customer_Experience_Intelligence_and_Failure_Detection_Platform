import { apiClient } from '@/app/api/client'

import type { AdministrationApiOverviewResponse } from './types'

export interface GetAdministrationOverviewOptions {
  signal?: AbortSignal
}

/**
 * Administration's first real API call (Step 7.X A-02) -- Platform
 * Overview's service-health data only; every other Administration
 * section remains presentation-only, unaffected by this module. Never
 * imports or references any individual backend service's URL; only the
 * centralized apiClient, which itself only knows the Gateway's base URL.
 */
export function getAdministrationOverview(
  options: GetAdministrationOverviewOptions = {},
): Promise<AdministrationApiOverviewResponse> {
  return apiClient.get<AdministrationApiOverviewResponse>('/administration/overview', {
    signal: options.signal,
  })
}
