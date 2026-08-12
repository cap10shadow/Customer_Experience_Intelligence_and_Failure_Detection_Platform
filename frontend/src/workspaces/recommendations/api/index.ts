export {
  getRecommendation,
  patchRecommendationDecision,
  type GetRecommendationOptions,
  type PatchRecommendationDecisionOptions,
} from './recommendationApi'
export type { RecommendationApiResponse, RecommendationDecisionApiValue, SupportingEvidenceApi } from './types'
export { toRecommendationViewModel, type RecommendationViewModel } from './viewModel'
