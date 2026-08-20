import { useCallback, useState } from 'react'

import { ApiError } from '@/app/api/errors'

import { approveMapping, bulkApproveMappings, rejectMapping } from '../api'

export interface UseFieldMappingActionsResult {
  /** Mapping ids with an approve/reject call currently in flight -- lets the UI disable just the affected row(s), not the whole list. */
  pendingIds: Set<string>
  error: ApiError | null
  /** "Accept" (targetValue = the suggestion) and "Change"/"Map" (any other targetValue) are both this call. */
  approve: (mappingId: string, targetValue: string, onDone: () => void) => Promise<void>
  /** One decision resolves every listed mapping id -- the bulk-approve action behind cluster multi-select. */
  bulkApprove: (mappingIds: string[], targetValue: string, onDone: () => void) => Promise<void>
  reject: (mappingId: string, onDone: () => void) => Promise<void>
}

/**
 * Thin wrapper around the field-mappings write endpoints, shared by
 * every mapping-review action in `MappingClusterList`. `onDone` is
 * always the analysis hook's `refresh()` -- re-running `:analyze` with
 * the same session id so the review UI reflects the just-approved
 * mapping immediately, without inflating occurrence counts.
 */
export function useFieldMappingActions(): UseFieldMappingActionsResult {
  const [pendingIds, setPendingIds] = useState<Set<string>>(new Set())
  const [error, setError] = useState<ApiError | null>(null)

  const withPending = useCallback(async (ids: string[], action: () => Promise<void>) => {
    setPendingIds((previous) => new Set([...previous, ...ids]))
    setError(null)
    try {
      await action()
    } catch (caught: unknown) {
      setError(caught instanceof ApiError ? caught : new ApiError({ code: 'UNKNOWN_ERROR', message: 'This mapping action failed.', status: 0 }))
    } finally {
      setPendingIds((previous) => {
        const next = new Set(previous)
        ids.forEach((id) => next.delete(id))
        return next
      })
    }
  }, [])

  const approve = useCallback(
    async (mappingId: string, targetValue: string, onDone: () => void) => {
      await withPending([mappingId], async () => {
        await approveMapping(mappingId, { target_value: targetValue })
        onDone()
      })
    },
    [withPending],
  )

  const bulkApprove = useCallback(
    async (mappingIds: string[], targetValue: string, onDone: () => void) => {
      await withPending(mappingIds, async () => {
        await bulkApproveMappings({ mapping_ids: mappingIds, target_value: targetValue })
        onDone()
      })
    },
    [withPending],
  )

  const reject = useCallback(
    async (mappingId: string, onDone: () => void) => {
      await withPending([mappingId], async () => {
        await rejectMapping(mappingId, {})
        onDone()
      })
    },
    [withPending],
  )

  return { pendingIds, error, approve, bulkApprove, reject }
}
