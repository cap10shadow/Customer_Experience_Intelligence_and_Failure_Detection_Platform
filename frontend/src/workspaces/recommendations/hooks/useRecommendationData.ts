import { useCallback, useEffect, useState } from 'react'

import { ApiError } from '@/app/api/errors'

import { getRecommendation, toRecommendationViewModel, type RecommendationViewModel } from '../api'

export interface UseRecommendationDataResult {
  data: RecommendationViewModel | null
  isLoading: boolean
  error: ApiError | null
  /** Issues a genuine new GET /api/v1/recommendations/:recommendationId request -- wired to ErrorBoundary's onRetry (Part 7) so "Try again" actually re-fetches instead of re-rendering the same stale error. */
  refetch: () => void
}

type RecommendationFetchState = Omit<UseRecommendationDataResult, 'refetch'>

const INITIAL_STATE: RecommendationFetchState = { data: null, isLoading: true, error: null }

/**
 * The Recommendation workspace's one data hook, following the pattern
 * established by useDashboardData/useInvestigationData -- Workspace ->
 * data hook -> API module -> centralized HTTP client -> Gateway. Takes
 * `recommendationId` directly (the canonical `/recommendations/
 * :recommendationId` route param) rather than reading it from
 * RecommendationContext, since -- unlike Investigation's incidentId --
 * it's already known before the Context/Provider tree exists.
 */
export function useRecommendationData(recommendationId: string | null): UseRecommendationDataResult {
  const [state, setState] = useState<RecommendationFetchState>(INITIAL_STATE)
  const [retryToken, setRetryToken] = useState(0)
  const refetch = useCallback(() => setRetryToken((token) => token + 1), [])

  useEffect(() => {
    if (!recommendationId) {
      return
    }

    const controller = new AbortController()

    // eslint-disable-next-line react-hooks/set-state-in-effect -- see useInvestigationData's identical, documented justification.
    setState((previous) => ({ ...previous, isLoading: true, error: null }))

    getRecommendation(recommendationId, { signal: controller.signal })
      .then((response) => {
        setState({ data: toRecommendationViewModel(response), isLoading: false, error: null })
      })
      .catch((caught: unknown) => {
        if (controller.signal.aborted) {
          return
        }
        setState((previous) => ({
          ...previous,
          isLoading: false,
          error:
            caught instanceof ApiError
              ? caught
              : new ApiError({ code: 'UNKNOWN_ERROR', message: 'Failed to load Recommendation data.', status: 0 }),
        }))
      })

    return () => controller.abort()
  }, [recommendationId, retryToken])

  if (!recommendationId) {
    return { data: null, isLoading: false, error: null, refetch }
  }

  return { ...state, refetch }
}
