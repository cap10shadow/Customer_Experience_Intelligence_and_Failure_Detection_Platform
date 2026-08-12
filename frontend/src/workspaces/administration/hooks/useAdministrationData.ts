import { useCallback, useEffect, useState } from 'react'

import { ApiError } from '@/app/api/errors'

import { getAdministrationOverview, toAdministrationViewModel, type AdministrationViewModel } from '../api'

export interface UseAdministrationDataResult {
  data: AdministrationViewModel | null
  isLoading: boolean
  error: ApiError | null
  /** Issues a genuine new GET /api/v1/administration/overview request -- wired to ErrorBoundary's onRetry so "Try again" actually re-fetches. */
  refetch: () => void
}

type AdministrationFetchState = Omit<UseAdministrationDataResult, 'refetch'>

const INITIAL_STATE: AdministrationFetchState = { data: null, isLoading: true, error: null }

/**
 * Administration's first real data hook (Step 7.X A-02), following the
 * same Workspace -> data hook -> API module -> centralized HTTP client ->
 * Gateway pattern already established by useDashboardData/
 * useInvestigationData. Fetches once on mount -- Platform Overview's
 * service-health data has no scope/filter dependency to react to, unlike
 * Dashboard's timeRange/region/etc.
 */
export function useAdministrationData(): UseAdministrationDataResult {
  const [state, setState] = useState<AdministrationFetchState>(INITIAL_STATE)
  const [retryToken, setRetryToken] = useState(0)
  const refetch = useCallback(() => setRetryToken((token) => token + 1), [])

  useEffect(() => {
    const controller = new AbortController()

    // eslint-disable-next-line react-hooks/set-state-in-effect -- see useDashboardData's identical, documented justification.
    setState((previous) => ({ ...previous, isLoading: true, error: null }))

    getAdministrationOverview({ signal: controller.signal })
      .then((response) => {
        setState({ data: toAdministrationViewModel(response), isLoading: false, error: null })
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
              : new ApiError({ code: 'UNKNOWN_ERROR', message: 'Failed to load Administration data.', status: 0 }),
        }))
      })

    return () => controller.abort()
  }, [retryToken])

  return { ...state, refetch }
}
