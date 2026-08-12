/**
 * Shape of GET /api/v1/recommendations/:recommendationId's response body
 * (backend/services/gateway_service/app/schemas/recommendations.py's
 * RecommendationResponse). Every field here is a real recommendation_service
 * field passed through the Gateway -- there is deliberately no confidence,
 * alternatives, risk, or expected-outcome field here, because
 * recommendation_service does not provide any of those today (Part 4's
 * backend capability audit).
 *
 * `decision`/`decisionNote`/`decidedAt` (Step 7.X G-01) are real, additive
 * fields: `null` until a human decision is actually persisted, never a
 * fabricated default.
 */
export interface SupportingEvidenceApi {
  source: string
  description: string
  weight: number
}

/** The four states recommendation_service's own RecommendationDecision enum defines (Step 7.X G-01). */
export type RecommendationDecisionApiValue = 'pending' | 'approved' | 'rejected' | 'deferred'

export interface RecommendationApiResponse {
  recommendationId: string
  incidentId: string
  generationId: string
  category: string
  priority: string
  score: number
  action: string
  recommendationRationale: string
  priorityRationale: string
  supportingEvidence: SupportingEvidenceApi[]
  createdAt: string
  decision: RecommendationDecisionApiValue | null
  decisionNote: string | null
  decidedAt: string | null
}
