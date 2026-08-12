import type { RationaleReason, RecommendationOverview } from '../types'
import type { RecommendationApiResponse } from './types'

/** The Recommendation workspace's own view model -- what RecommendationsWorkspace hands down to its sections. */
export interface RecommendationViewModel {
  recommendationId: string
  incidentId: string
  overview: RecommendationOverview
  rationale: RationaleReason
}

function toTitleCase(value: string): string {
  return value
    .split('_')
    .map((word) => (word ? word[0].toUpperCase() + word.slice(1) : word))
    .join(' ')
}

/**
 * Adapts the Gateway's RecommendationResponse into the Recommendation
 * workspace's view model. recommendation_service provides exactly two
 * explanatory text fields -- `recommendationRationale` (why this was
 * recommended) and `priorityRationale` (why this priority) -- so both
 * Overview's `summary` and Rationale's `explanation` draw on the same real
 * `recommendationRationale` text rather than inventing a distinct one;
 * Rationale's `headline` uses the real `priorityRationale` sentence rather
 * than a fabricated label. Nothing here invents confidence, alternatives,
 * risk, expected outcome, or decision/lifecycle state -- those sections
 * remain FutureCapabilityPlaceholder/illustrative, as none of that data
 * exists on the backend today (Part 4's capability audit).
 */
export function toRecommendationViewModel(response: RecommendationApiResponse): RecommendationViewModel {
  return {
    recommendationId: response.recommendationId,
    incidentId: response.incidentId,
    overview: {
      headline: response.action,
      summary: response.recommendationRationale,
      category: toTitleCase(response.category),
      priority: toTitleCase(response.priority),
    },
    rationale: {
      headline: response.priorityRationale,
      explanation: response.recommendationRationale,
    },
  }
}
