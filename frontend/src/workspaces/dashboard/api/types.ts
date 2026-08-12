import type {
  CriticalSituation,
  DecisionOpportunity,
  EvidenceItem,
  FocusArea,
  HealthIndicator,
  KeyChange,
  OperationalStateLevel,
  OperationalStory,
} from '../types'

/**
 * Shape of GET /api/v1/dashboard's response body
 * (backend/services/gateway_service/app/schemas/dashboard.py's
 * DashboardResponse). Field shapes were deliberately designed to match
 * the Dashboard's existing presentation types 1:1, so the view-model
 * adapter (./viewModel.ts) is close to an identity mapping rather than a
 * heavy transformation -- there was no frontend/backend shape mismatch
 * left to reconcile once the DTO was designed against these types.
 */
export interface DashboardApiOperationalBrief {
  level: OperationalStateLevel
  summary: string
  healthIndicators: HealthIndicator[]
  criticalSituations: CriticalSituation[]
  keyChanges: KeyChange[]
  focusAreas: FocusArea[]
}

export interface DashboardApiAppliedFilters {
  timeRange: string
  region: string | null
  businessUnit: string | null
  productScope: string | null
  userScope: string | null
}

export interface DashboardApiResponse {
  operationalBrief: DashboardApiOperationalBrief
  decisionSummary: DecisionOpportunity[]
  investigationEntryPoints: OperationalStory[]
  appliedFilters: DashboardApiAppliedFilters
  /** Real, factual trend summaries from anomaly_service's existing per-dimension trend endpoints (Step 7.X A-01). */
  supportingEvidence: EvidenceItem[]
  /** Human-readable notes about any non-essential source that was unavailable when this response was built. Empty when everything succeeded. */
  warnings: string[]
}
