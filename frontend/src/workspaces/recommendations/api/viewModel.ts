import type { DecisionRecord, DecisionStatus, RationaleReason, RecommendationOverview } from '../types'
import type { RecommendationApiResponse, RecommendationDecisionApiValue } from './types'

/** The Recommendation workspace's own view model -- what RecommendationsWorkspace hands down to its sections. */
export interface RecommendationViewModel {
  recommendationId: string
  incidentId: string
  overview: RecommendationOverview
  rationale: RationaleReason
  /** Undefined only when no decision has ever been persisted (backend `decision` is null) -- never a fabricated 'pending-review' default (Step 7.X G-01/A-07). */
  decision?: DecisionRecord
}

/** recommendation_service's own `pending` maps to this workspace's `pending-review` -- every other value is already a 1:1 match. */
function toDecisionStatus(decision: RecommendationDecisionApiValue): DecisionStatus {
  return decision === 'pending' ? 'pending-review' : decision
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
 * risk, or expected outcome -- those sections remain
 * FutureCapabilityPlaceholder/illustrative, as none of that data exists on
 * the backend today (Part 4's capability audit). `decision` (Step 7.X
 * G-01) is the one exception: real, persisted decision state, mapped only
 * when the backend actually has one.
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
    decision: response.decision
      ? { status: toDecisionStatus(response.decision), note: response.decisionNote ?? '' }
      : undefined,
  }
}
