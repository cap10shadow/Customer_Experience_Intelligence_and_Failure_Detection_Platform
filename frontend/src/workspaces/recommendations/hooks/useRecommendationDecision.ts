import { useCallback, useState } from 'react'

import { ApiError } from '@/app/api/errors'

import { patchRecommendationDecision } from '../api'
import type { RecommendationDecisionApiValue } from '../api'

export interface UseRecommendationDecisionResult {
  isSubmitting: boolean
  error: ApiError | null
  /** Submits the real PATCH /api/v1/recommendations/:recommendationId/decision request (Step 7.X G-01); resolves once the backend has genuinely persisted the decision. */
  submit: (decision: RecommendationDecisionApiValue, note: string | undefined) => Promise<void>
}

/**
 * The Recommendation workspace's one write hook (Step 7.X G-01),
 * separate from `useRecommendationData` (the read hook) since a mutation
 * has a distinct in-flight/error lifecycle from a fetch. Callers are
 * responsible for re-reading real state afterward (e.g. via
 * `useRecommendationData`'s `refetch`) -- this hook never fabricates or
 * optimistically assumes the new decision locally.
 */
export function useRecommendationDecision(recommendationId: string | null): UseRecommendationDecisionResult {
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<ApiError | null>(null)

  const submit = useCallback(
    async (decision: RecommendationDecisionApiValue, note: string | undefined) => {
      if (!recommendationId) {
        return
      }
      setIsSubmitting(true)
      setError(null)
      try {
        await patchRecommendationDecision(recommendationId, decision, note)
      } catch (caught: unknown) {
        setError(
          caught instanceof ApiError
            ? caught
            : new ApiError({ code: 'UNKNOWN_ERROR', message: 'Failed to record the decision.', status: 0 }),
        )
        throw caught
      } finally {
        setIsSubmitting(false)
      }
    },
    [recommendationId],
  )

  return { isSubmitting, error, submit }
}
