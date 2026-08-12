import { useCallback, useEffect, useState } from 'react'

import { ApiError } from '@/app/api/errors'

import { useInvestigationContext } from '../context'
import { getInvestigation, toInvestigationViewModel, type InvestigationViewModel } from '../api'

export interface UseInvestigationDataResult {
  data: InvestigationViewModel | null
  isLoading: boolean
  error: ApiError | null
  /** Issues a genuine new GET /api/v1/investigations/:incidentId request -- wired to ErrorBoundary's onRetry (Part 7) so "Try again" actually re-fetches instead of re-rendering the same stale error. */
  refetch: () => void
}

type InvestigationFetchState = Omit<UseInvestigationDataResult, 'refetch'>

const INITIAL_STATE: InvestigationFetchState = { data: null, isLoading: true, error: null }

/**
 * The Investigation workspace's one data hook, following the pattern
 * established by useDashboardData -- Workspace -> data hook -> API
 * module -> centralized HTTP client -> Gateway. Reads `incidentId` from
 * InvestigationContext (populated from the canonical `/investigations/
 * :incidentId` route param by InvestigationsWorkspace) and re-fetches
 * whenever it changes.
 */
export function useInvestigationData(): UseInvestigationDataResult {
  const { incidentId } = useInvestigationContext()

  const [state, setState] = useState<InvestigationFetchState>(INITIAL_STATE)
  const [retryToken, setRetryToken] = useState(0)
  const refetch = useCallback(() => setRetryToken((token) => token + 1), [])

  useEffect(() => {
    if (!incidentId) {
      // Nothing to fetch -- derived directly in the return below rather
      // than via a setState call here (there's no async work to kick off
      // in this branch, so an effect isn't actually needed for it).
      return
    }

    const controller = new AbortController()

    // eslint-disable-next-line react-hooks/set-state-in-effect -- see useDashboardData's identical, documented justification.
    setState((previous) => ({ ...previous, isLoading: true, error: null }))

    getInvestigation(incidentId, { signal: controller.signal })
      .then((response) => {
        setState({ data: toInvestigationViewModel(response), isLoading: false, error: null })
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
              : new ApiError({ code: 'UNKNOWN_ERROR', message: 'Failed to load Investigation data.', status: 0 }),
        }))
      })

    return () => controller.abort()
  }, [incidentId, retryToken])

  if (!incidentId) {
    return { data: null, isLoading: false, error: null, refetch }
  }

  return { ...state, refetch }
}
