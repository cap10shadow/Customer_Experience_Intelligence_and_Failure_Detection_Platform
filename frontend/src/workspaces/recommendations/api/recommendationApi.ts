import { apiClient } from '@/app/api/client'

import type { RecommendationApiResponse } from './types'

export interface GetRecommendationOptions {
  signal?: AbortSignal
}

/**
 * The Recommendation workspace's only API module -- one Gateway call per
 * recommendationId (Batch 4A SS8: a single-service read, not an
 * aggregation). Never imports or references recommendation_service's own
 * URL directly; only the centralized apiClient.
 */
export function getRecommendation(
  recommendationId: string,
  options: GetRecommendationOptions = {},
): Promise<RecommendationApiResponse> {
  return apiClient.get<RecommendationApiResponse>(`/recommendations/${encodeURIComponent(recommendationId)}`, {
    signal: options.signal,
  })
}
