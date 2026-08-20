import { apiClient } from '@/app/api/client'

import type { DashboardApiResponse } from './types'

export interface DashboardApiQuery {
  /** Required (docs/DECISIONS.md AD-12) -- the Gateway rejects a Dashboard request with no Dataset scope, since there is no "all datasets combined" view. */
  datasetId: string
  timeRange: string
  region?: string | null
  businessUnit?: string | null
  productScope?: string | null
  userScope?: string | null
}

export interface GetDashboardOptions {
  signal?: AbortSignal
}

/**
 * The Dashboard's only API module -- everything the workspace needs comes
 * from this one Gateway call (per Batch 1 SS2/SS7: the Gateway aggregates,
 * the frontend never assembles a workspace from multiple direct backend
 * calls). Never imports or references any individual backend service's
 * URL; only the centralized apiClient, which itself only knows the
 * Gateway's base URL.
 */
export function getDashboard(query: DashboardApiQuery, options: GetDashboardOptions = {}): Promise<DashboardApiResponse> {
  return apiClient.get<DashboardApiResponse>('/v1/dashboard', {
    query: {
      datasetId: query.datasetId,
      timeRange: query.timeRange,
      region: query.region ?? undefined,
      businessUnit: query.businessUnit ?? undefined,
      productScope: query.productScope ?? undefined,
      userScope: query.userScope ?? undefined,
    },
    signal: options.signal,
  })
}
