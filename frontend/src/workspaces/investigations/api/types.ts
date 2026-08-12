import type {
  BusinessImpactDimensionSummary,
  ConfidenceLevel,
  EvidenceItem,
  RecommendedAction,
  RootCauseExplanation,
} from '../types'

/**
 * Shape of GET /api/v1/investigations/:incidentId's response body
 * (backend/services/gateway_service/app/schemas/investigation.py's
 * InvestigationResponse). Field shapes match the Investigation
 * workspace's existing presentation types 1:1 -- the DTO was designed
 * against those types directly.
 */
export interface InvestigationApiObservation {
  headline: string
  description: string
}

export interface InvestigationApiResponse {
  incidentId: string
  observation: InvestigationApiObservation
  evidence: EvidenceItem[]
  /** null = not yet analyzed (a legitimate domain state), not a failure. */
  rootCause: RootCauseExplanation | null
  /** empty = not yet assessed (a legitimate domain state), not a failure. */
  businessImpact: BusinessImpactDimensionSummary[]
  businessImpactConfidenceLevel: ConfidenceLevel | null
  /** null = no recommendation generated yet for this incident. */
  recommendedNextStep: RecommendedAction | null
  /** Human-readable notes about any non-essential source that was unavailable when this response was built. */
  warnings: string[]
}
