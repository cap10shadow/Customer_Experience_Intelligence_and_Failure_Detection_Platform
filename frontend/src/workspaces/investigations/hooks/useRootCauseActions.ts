import { useCallback, useState } from 'react'

import { ApiError } from '@/app/api/errors'

import { confirmRootCause, refreshRootCause, rejectRootCause } from '../api'

export type RootCauseActionName = 'confirm' | 'reject' | 'refresh'

export interface UseRootCauseActionsResult {
  /** Which action is currently in flight, if any -- lets the UI disable only the button that was pressed rather than the whole row. */
  pendingAction: RootCauseActionName | null
  error: ApiError | null
  confirm: () => Promise<void>
  reject: () => Promise<void>
  refresh: () => Promise<void>
}

/**
 * The Investigation workspace's root-cause lifecycle write hook, mirroring
 * `useRecommendationDecision`'s pattern: a mutation has a distinct
 * in-flight/error lifecycle from the read hook (`useInvestigationData`).
 * Callers are responsible for re-reading real state afterward (`refetch`)
 * -- this hook never fabricates or optimistically assumes the new status.
 */
export function useRootCauseActions(incidentId: string | null): UseRootCauseActionsResult {
  const [pendingAction, setPendingAction] = useState<RootCauseActionName | null>(null)
  const [error, setError] = useState<ApiError | null>(null)

  const run = useCallback(
    async (action: RootCauseActionName, call: (incidentId: string) => Promise<unknown>) => {
      if (!incidentId) {
        return
      }
      setPendingAction(action)
      setError(null)
      try {
        await call(incidentId)
      } catch (caught: unknown) {
        setError(
          caught instanceof ApiError
            ? caught
            : new ApiError({ code: 'UNKNOWN_ERROR', message: `Failed to ${action} the root cause.`, status: 0 }),
        )
        throw caught
      } finally {
        setPendingAction(null)
      }
    },
    [incidentId],
  )

  return {
    pendingAction,
    error,
    confirm: () => run('confirm', confirmRootCause),
    reject: () => run('reject', rejectRootCause),
    refresh: () => run('refresh', refreshRootCause),
  }
}
