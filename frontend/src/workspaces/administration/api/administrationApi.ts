import { apiClient } from '@/app/api/client'

import type { AdministrationApiIntelligenceConfigurationResponse, AdministrationApiOverviewResponse } from './types'

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

export interface GetIntelligenceConfigurationOptions {
  signal?: AbortSignal
}

/**
 * Read-only Business Impact configuration (Step 7.X G-05) -- real,
 * currently-active engine values only. Read-only by construction: this
 * module has no corresponding write function.
 */
export function getIntelligenceConfiguration(
  options: GetIntelligenceConfigurationOptions = {},
): Promise<AdministrationApiIntelligenceConfigurationResponse> {
  return apiClient.get<AdministrationApiIntelligenceConfigurationResponse>('/administration/intelligence-configuration', {
    signal: options.signal,
  })
}
