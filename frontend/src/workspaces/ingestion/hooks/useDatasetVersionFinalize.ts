import { useCallback, useState } from 'react'

import { ApiError } from '@/app/api/errors'

import { finalizeDatasetVersion, toDatasetVersion } from '../api'
import type { DatasetVersion } from '../types'

export interface UseDatasetVersionFinalizeResult {
  isSubmitting: boolean
  result: DatasetVersion | null
  error: ApiError | null
  /** Closes the dataset's current draft into a real, numbered version and drives the full analysis pipeline. The Gateway call is synchronous end-to-end -- this resolves only once the real pipeline has reached a terminal status (ready/failed/partially_completed), never early. */
  finalize: (datasetId: string) => Promise<DatasetVersion | null>
  reset: () => void
}

/**
 * The Data workspace's "Finalize & Analyze" write hook -- the trigger for
 * both the "new dataset" and "extend dataset" flows once rows have been
 * ingested into the dataset's open draft (docs/DECISIONS.md AD-12).
 */
export function useDatasetVersionFinalize(): UseDatasetVersionFinalizeResult {
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [result, setResult] = useState<DatasetVersion | null>(null)
  const [error, setError] = useState<ApiError | null>(null)

  const finalize = useCallback(async (datasetId: string): Promise<DatasetVersion | null> => {
    setIsSubmitting(true)
    setError(null)
    try {
      const response = await finalizeDatasetVersion(datasetId)
      const version = toDatasetVersion(response)
      setResult(version)
      return version
    } catch (caught: unknown) {
      const apiError =
        caught instanceof ApiError
          ? caught
          : new ApiError({ code: 'UNKNOWN_ERROR', message: 'Failed to finalize this dataset version.', status: 0 })
      setError(apiError)
      return null
    } finally {
      setIsSubmitting(false)
    }
  }, [])

  const reset = useCallback(() => {
    setResult(null)
    setError(null)
  }, [])

  return { isSubmitting, result, error, finalize, reset }
}
