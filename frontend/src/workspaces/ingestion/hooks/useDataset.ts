import { useCallback, useEffect, useState } from 'react'

import { ApiError } from '@/app/api/errors'

import { getDataset, toDatasetDetail } from '../api'
import type { DatasetDetail } from '../types'

export interface UseDatasetResult {
  data: DatasetDetail | null
  isLoading: boolean
  error: ApiError | null
  refetch: () => void
}

type FetchState = Omit<UseDatasetResult, 'refetch'>

const INITIAL_STATE: FetchState = { data: null, isLoading: true, error: null }

/** One dataset's detail (real version history included) -- `GET /api/v1/datasets/{id}`. `datasetId` of `null` fetches nothing. */
export function useDataset(datasetId: string | null): UseDatasetResult {
  const [state, setState] = useState<FetchState>(INITIAL_STATE)
  const [retryToken, setRetryToken] = useState(0)
  const refetch = useCallback(() => setRetryToken((token) => token + 1), [])

  useEffect(() => {
    if (!datasetId) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- mirrors useInvestigationData's identical "nothing to fetch" branch.
      setState({ data: null, isLoading: false, error: null })
      return
    }

    const controller = new AbortController()

    // eslint-disable-next-line react-hooks/set-state-in-effect
    setState((previous) => ({ ...previous, isLoading: true, error: null }))

    getDataset(datasetId, { signal: controller.signal })
      .then((response) => {
        setState({ data: toDatasetDetail(response), isLoading: false, error: null })
      })
      .catch((caught: unknown) => {
        if (controller.signal.aborted) return
        setState((previous) => ({
          ...previous,
          isLoading: false,
          error:
            caught instanceof ApiError
              ? caught
              : new ApiError({ code: 'UNKNOWN_ERROR', message: 'Failed to load this dataset.', status: 0 }),
        }))
      })

    return () => controller.abort()
  }, [datasetId, retryToken])

  return { ...state, refetch }
}
