/**
 * Stage-specific confidence vocabulary (ARB-008: confidence is never a
 * single universal score -- Root Cause certainty and Business Impact
 * completeness are different measurements that happen to share a
 * three-level scale for presentation consistency only). Every value
 * using this type must always be paired with a `measures` string
 * stating what it actually measures -- see `ConfidencePresentation`.
 */
export type ConfidenceLevel = 'low' | 'moderate' | 'high'

/** One stage of the Evidence Chain (ARB-006) contributing to this Incident's story. */
export type EvidenceSource = 'NLP Intelligence' | 'Anomaly Detection' | 'Incident Correlation' | 'Root Cause Analysis'

export interface EvidenceItem {
  id: string
  headline: string
  detail: string
  source: EvidenceSource
}

/** Mirrors root_cause_service's own RootCauseStatus enum, surfaced through the Gateway (RootCauseExplanationDTO.status). */
export type RootCauseLifecycleStatus = 'identified' | 'confirmed' | 'rejected'

export const ROOT_CAUSE_STATUS_LABEL: Record<RootCauseLifecycleStatus, string> = {
  identified: 'Awaiting review',
  confirmed: 'Confirmed',
  rejected: 'Rejected',
}

export interface RootCauseExplanation {
  headline: string
  reasoning: string
  confidenceLevel: ConfidenceLevel
  status: RootCauseLifecycleStatus
}

/**
 * The five Business Impact dimensions, always evaluated together, per
 * BI-002 / ARB-003 / PRD.md -- never a subset, never an invented
 * alternative dimension.
 */
export type BusinessImpactDimension = 'financial' | 'customer' | 'operational' | 'sla' | 'reputation'

export const BUSINESS_IMPACT_DIMENSION_LABEL: Record<BusinessImpactDimension, string> = {
  financial: 'Financial',
  customer: 'Customer',
  operational: 'Operational',
  sla: 'SLA',
  reputation: 'Reputation',
}

export interface BusinessImpactDimensionSummary {
  dimension: BusinessImpactDimension
  headline: string
  detail: string
}

export interface RecommendedAction {
  headline: string
  reason: string
  /** The Recommendation this Incident produced, if any -- carried in the transition link so a future step can open Recommendations pre-scoped to it (see docs/DECISIONS.md, FE-001 and the Step 3 Architecture Review, item 4). Not consumed by Recommendations yet. */
  recommendationId?: string
}
