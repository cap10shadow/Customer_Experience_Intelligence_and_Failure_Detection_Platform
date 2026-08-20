import { useCallback, useEffect, useState } from 'react'

import { ApiError } from '@/app/api/errors'

import { listDatasets, toDatasetSummary } from '../api'
import type { DatasetSummary } from '../types'

export interface UseDatasetsResult {
  data: DatasetSummary[] | null
  isLoading: boolean
  error: ApiError | null
  refetch: () => void
}

type FetchState = Omit<UseDatasetsResult, 'refetch'>

const INITIAL_STATE: FetchState = { data: null, isLoading: true, error: null }

/** The Data workspace's dataset-list read hook (`GET /api/v1/datasets`) -- the entry point into every other dataset-aware workspace. */
export function useDatasets(): UseDatasetsResult {
  const [state, setState] = useState<FetchState>(INITIAL_STATE)
  const [retryToken, setRetryToken] = useState(0)
  const refetch = useCallback(() => setRetryToken((token) => token + 1), [])

  useEffect(() => {
    const controller = new AbortController()

    // eslint-disable-next-line react-hooks/set-state-in-effect -- see useDashboardData's identical, documented justification.
    setState((previous) => ({ ...previous, isLoading: true, error: null }))

    listDatasets({ signal: controller.signal })
      .then((response) => {
        setState({ data: response.map(toDatasetSummary), isLoading: false, error: null })
      })
      .catch((caught: unknown) => {
        if (controller.signal.aborted) return
        setState((previous) => ({
          ...previous,
          isLoading: false,
          error:
            caught instanceof ApiError
              ? caught
              : new ApiError({ code: 'UNKNOWN_ERROR', message: 'Failed to load datasets.', status: 0 }),
        }))
      })

    return () => controller.abort()
  }, [retryToken])

  return { ...state, refetch }
}
