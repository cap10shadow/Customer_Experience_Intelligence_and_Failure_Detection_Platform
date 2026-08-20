import { useCallback, useEffect, useState } from 'react'

import { ApiError } from '@/app/api/errors'
import { useDatasetContext } from '@/app/context/DatasetContext'

import { useAnalyticsContext } from '../context'
import { getAnalytics, toAnalyticsViewModel, type AnalyticsViewModel } from '../api'

export interface UseAnalyticsDataResult {
  data: AnalyticsViewModel | null
  isLoading: boolean
  error: ApiError | null
  /** Issues a genuine new GET /api/v1/analytics/trends request -- wired to ErrorBoundary's onRetry (Part 7) so "Try again" actually re-fetches instead of re-rendering the same stale error. */
  refetch: () => void
}

type AnalyticsFetchState = Omit<UseAnalyticsDataResult, 'refetch'>

const INITIAL_STATE: AnalyticsFetchState = { data: null, isLoading: true, error: null }

/**
 * The Analytics workspace's one data hook, following the pattern
 * established by useDashboardData -- Workspace -> data hook -> API
 * module -> centralized HTTP client -> Gateway. Reads `selectedAnalysisPeriod`
 * from AnalyticsContext (UX-005's one shared scope) and re-fetches
 * whenever it changes, exactly as useDashboardData reacts to timeRange.
 *
 * Also reads the global `selectedDatasetId` (docs/DECISIONS.md AD-12):
 * the Gateway's `/analytics/trends` route requires a `datasetId` and has
 * no "all datasets" fallback, so this hook fetches nothing at all --
 * never a global/unscoped request -- while no dataset is selected.
 */
export function useAnalyticsData(): UseAnalyticsDataResult {
  const { selectedAnalysisPeriod } = useAnalyticsContext()
  const { selectedDatasetId } = useDatasetContext()

  const [state, setState] = useState<AnalyticsFetchState>(INITIAL_STATE)
  const [retryToken, setRetryToken] = useState(0)
  const refetch = useCallback(() => setRetryToken((token) => token + 1), [])

  useEffect(() => {
    if (!selectedDatasetId) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- mirrors useDataset's identical "nothing to fetch" branch.
      setState({ data: null, isLoading: false, error: null })
      return
    }

    const controller = new AbortController()

    // eslint-disable-next-line react-hooks/set-state-in-effect -- see useDashboardData's identical, documented justification.
    setState((previous) => ({ ...previous, isLoading: true, error: null }))

    getAnalytics({ datasetId: selectedDatasetId, period: selectedAnalysisPeriod }, { signal: controller.signal })
      .then((response) => {
        setState({ data: toAnalyticsViewModel(response), isLoading: false, error: null })
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
              : new ApiError({ code: 'UNKNOWN_ERROR', message: 'Failed to load Analytics data.', status: 0 }),
        }))
      })

    return () => controller.abort()
  }, [selectedDatasetId, selectedAnalysisPeriod, retryToken])

  return { ...state, refetch }
}
