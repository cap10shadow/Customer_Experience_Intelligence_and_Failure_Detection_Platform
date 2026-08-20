import { useCallback, useEffect, useState } from 'react'

import { ApiError } from '@/app/api/errors'
import { useDatasetContext } from '@/app/context/DatasetContext'

import { useDashboardContext } from '../context'
import { getDashboard, toDashboardViewModel, type DashboardViewModel } from '../api'

export interface UseDashboardDataResult {
  data: DashboardViewModel | null
  isLoading: boolean
  error: ApiError | null
  /** Issues a genuine new GET /api/v1/dashboard request -- wired to ErrorBoundary's onRetry (Part 7) so "Try again" actually re-fetches instead of re-rendering the same stale error. */
  refetch: () => void
}

type DashboardFetchState = Omit<UseDashboardDataResult, 'refetch'>

const INITIAL_STATE: DashboardFetchState = { data: null, isLoading: true, error: null }

/**
 * The Dashboard workspace's one data hook -- per Batch 1 SS7's
 * Workspace -> data hook -> API module -> HTTP client -> Gateway chain.
 * Reads DashboardContext's existing scope fields (timeRange/region/
 * businessUnit/productScope/userScope) and re-fetches whenever any of
 * them change, so the day a filter bar actually calls setRegion/etc.
 * this already reacts correctly -- no rework needed here.
 *
 * Also reads the global `selectedDatasetId` (docs/DECISIONS.md AD-12):
 * the Gateway's `/dashboard` route requires a `datasetId` and has no
 * "all datasets" fallback, so this hook fetches nothing at all -- never
 * a global/unscoped request -- while no dataset is selected.
 */
export function useDashboardData(): UseDashboardDataResult {
  const { timeRange, region, businessUnit, productScope, userScope } = useDashboardContext()
  const { selectedDatasetId } = useDatasetContext()

  const [state, setState] = useState<DashboardFetchState>(INITIAL_STATE)
  const [retryToken, setRetryToken] = useState(0)
  const refetch = useCallback(() => setRetryToken((token) => token + 1), [])

  useEffect(() => {
    if (!selectedDatasetId) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- mirrors useDataset's identical "nothing to fetch" branch.
      setState({ data: null, isLoading: false, error: null })
      return
    }

    const controller = new AbortController()

    // Resets to "loading" for this effect run -- only exercised once
    // timeRange/region/etc. actually change (no filter control calls the
    // context setters yet), but required regardless for correctness once
    // one does. This is the standard fetch-in-effect transition, not an
    // accidental cascade: the frozen architecture (Batch 1 SS7) requires
    // native fetch behind one centralized client rather than a
    // query library whose internal state machine would avoid this pattern.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setState((previous) => ({ ...previous, isLoading: true, error: null }))

    getDashboard(
      { datasetId: selectedDatasetId, timeRange, region, businessUnit, productScope, userScope },
      { signal: controller.signal },
    )
      .then((response) => {
        setState({ data: toDashboardViewModel(response), isLoading: false, error: null })
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
              : new ApiError({ code: 'UNKNOWN_ERROR', message: 'Failed to load Dashboard data.', status: 0 }),
        }))
      })

    return () => controller.abort()
  }, [selectedDatasetId, timeRange, region, businessUnit, productScope, userScope, retryToken])

  return { ...state, refetch }
}
