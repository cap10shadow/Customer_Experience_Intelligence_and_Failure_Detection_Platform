import { apiClient } from '@/app/api/client'

import type { AnalysisPeriod } from '../types'
import type { AnalyticsApiResponse } from './types'

export interface AnalyticsApiQuery {
  /** Required (docs/DECISIONS.md AD-12) -- there is no "all datasets" trend view. */
  datasetId: string
  period: AnalysisPeriod
}

export interface GetAnalyticsOptions {
  signal?: AbortSignal
}

/**
 * The Analytics workspace's only API module -- one Gateway call for the
 * real trend capability (Batch 1 SS2/SS7: the Gateway aggregates, the
 * frontend never calls anomaly_service directly). Never imports or
 * references anomaly_service's own URL; only the centralized apiClient.
 */
export function getAnalytics(query: AnalyticsApiQuery, options: GetAnalyticsOptions = {}): Promise<AnalyticsApiResponse> {
  return apiClient.get<AnalyticsApiResponse>('/v1/analytics/trends', {
    query: { datasetId: query.datasetId, period: query.period },
    signal: options.signal,
  })
}
