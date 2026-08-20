import { apiClient } from '@/app/api/client'

import type { RecommendationApiResponse, RecommendationDecisionApiValue } from './types'

export interface GetRecommendationOptions {
  signal?: AbortSignal
}

/**
 * The Recommendation workspace's read API call -- one Gateway call per
 * recommendationId (Batch 4A SS8: a single-service read, not an
 * aggregation). Never imports or references recommendation_service's own
 * URL directly; only the centralized apiClient.
 */
export function getRecommendation(
  recommendationId: string,
  options: GetRecommendationOptions = {},
): Promise<RecommendationApiResponse> {
  return apiClient.get<RecommendationApiResponse>(`/v1/recommendations/${encodeURIComponent(recommendationId)}`, {
    signal: options.signal,
  })
}

export interface PatchRecommendationDecisionOptions {
  signal?: AbortSignal
}

/**
 * Records a decision against this Recommendation (Step 7.X G-01) -- the
 * workspace's one write call, through the same centralized apiClient and
 * Gateway boundary as every read. Never sends an actor/owner field or a
 * client-supplied timestamp: the server sets `decidedAt`.
 */
export function patchRecommendationDecision(
  recommendationId: string,
  decision: RecommendationDecisionApiValue,
  note: string | undefined,
  options: PatchRecommendationDecisionOptions = {},
): Promise<RecommendationApiResponse> {
  return apiClient.patch<RecommendationApiResponse>(
    `/v1/recommendations/${encodeURIComponent(recommendationId)}/decision`,
    { decision, note },
    { signal: options.signal },
  )
}
