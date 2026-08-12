import { useCallback, useEffect, useState } from 'react'

import { ApiError } from '@/app/api/errors'

import { getIntelligenceConfiguration, toIntelligenceConfigurationViewModel, type IntelligenceConfigurationViewModel } from '../api'

export interface UseIntelligenceConfigurationDataResult {
  data: IntelligenceConfigurationViewModel | null
  isLoading: boolean
  error: ApiError | null
  /** Issues a genuine new GET /api/v1/administration/intelligence-configuration request -- wired to ErrorBoundary's onRetry so "Try again" actually re-fetches. */
  refetch: () => void
}

type IntelligenceConfigurationFetchState = Omit<UseIntelligenceConfigurationDataResult, 'refetch'>

const INITIAL_STATE: IntelligenceConfigurationFetchState = { data: null, isLoading: true, error: null }

/**
 * Intelligence Configuration's real data hook (Step 7.X G-05), separate
 * from `useAdministrationData` (Platform Overview's own real data
 * source) since each section fetches independently -- a failure in one
 * never blocks the other, matching this workspace's per-section
 * error-isolation discipline.
 */
export function useIntelligenceConfigurationData(): UseIntelligenceConfigurationDataResult {
  const [state, setState] = useState<IntelligenceConfigurationFetchState>(INITIAL_STATE)
  const [retryToken, setRetryToken] = useState(0)
  const refetch = useCallback(() => setRetryToken((token) => token + 1), [])

  useEffect(() => {
    const controller = new AbortController()

    // eslint-disable-next-line react-hooks/set-state-in-effect -- see useAdministrationData's identical, documented justification.
    setState((previous) => ({ ...previous, isLoading: true, error: null }))

    getIntelligenceConfiguration({ signal: controller.signal })
      .then((response) => {
        setState({ data: toIntelligenceConfigurationViewModel(response), isLoading: false, error: null })
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
              : new ApiError({ code: 'UNKNOWN_ERROR', message: 'Failed to load Intelligence Configuration data.', status: 0 }),
        }))
      })

    return () => controller.abort()
  }, [retryToken])

  return { ...state, refetch }
}
