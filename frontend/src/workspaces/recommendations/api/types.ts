/**
 * Shape of GET /api/v1/recommendations/:recommendationId's response body
 * (backend/services/gateway_service/app/schemas/recommendations.py's
 * RecommendationResponse). Every field here is a real recommendation_service
 * field passed through the Gateway -- there is deliberately no confidence,
 * alternatives, risk, expected-outcome, or decision/lifecycle field here,
 * because recommendation_service does not provide any of those today
 * (Part 4's backend capability audit).
 */
export interface SupportingEvidenceApi {
  source: string
  description: string
  weight: number
}

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
}
