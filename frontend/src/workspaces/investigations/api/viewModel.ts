import type {
  BusinessImpactDimensionSummary,
  ConfidenceLevel,
  EvidenceItem,
  RecommendedAction,
  RootCauseExplanation,
} from '../types'
import type { InvestigationApiObservation, InvestigationApiResponse } from './types'

/** The Investigation workspace's own view model -- what InvestigationsWorkspace hands down to its five sections. */
export interface InvestigationViewModel {
  datasetId: string
  datasetVersionId: string
  observation: InvestigationApiObservation
  evidence: EvidenceItem[]
  rootCause: RootCauseExplanation | null
  businessImpact: BusinessImpactDimensionSummary[]
  businessImpactConfidenceLevel: ConfidenceLevel | null
  recommendedNextStep: RecommendedAction | null
  warnings: string[]
}

/**
 * Adapts the Gateway's InvestigationResponse into the Investigation
 * workspace's view model. Thin by design: the Gateway DTO's shape was
 * designed against these same presentation types (see ./types.ts).
 */
export function toInvestigationViewModel(response: InvestigationApiResponse): InvestigationViewModel {
  return {
    datasetId: response.datasetId,
    datasetVersionId: response.datasetVersionId,
    observation: response.observation,
    evidence: response.evidence,
    rootCause: response.rootCause,
    businessImpact: response.businessImpact,
    businessImpactConfidenceLevel: response.businessImpactConfidenceLevel,
    recommendedNextStep: response.recommendedNextStep,
    warnings: response.warnings,
  }
}
