import { useCallback, useState } from 'react'

import { ApiError } from '@/app/api/errors'

import { archiveDataset } from '../api'

export interface UseDatasetArchiveResult {
  isArchiving: boolean
  error: ApiError | null
  /** Archives (soft-deletes) a dataset -- returns true on success. Its versions/complaints/downstream intelligence are left completely intact; it only stops appearing in listings/lookups. */
  archive: (datasetId: string) => Promise<boolean>
  reset: () => void
}

/** The Data workspace's "Archive dataset" write hook (WP-D dataset lifecycle). */
export function useDatasetArchive(): UseDatasetArchiveResult {
  const [isArchiving, setIsArchiving] = useState(false)
  const [error, setError] = useState<ApiError | null>(null)

  const archive = useCallback(async (datasetId: string): Promise<boolean> => {
    setIsArchiving(true)
    setError(null)
    try {
      await archiveDataset(datasetId)
      return true
    } catch (caught: unknown) {
      const apiError =
        caught instanceof ApiError ? caught : new ApiError({ code: 'UNKNOWN_ERROR', message: 'Failed to archive this dataset.', status: 0 })
      setError(apiError)
      return false
    } finally {
      setIsArchiving(false)
    }
  }, [])

  const reset = useCallback(() => {
    setError(null)
  }, [])

  return { isArchiving, error, archive, reset }
}
