import { AdvisoryNotice } from '@/shared/components/feedback'
import { Stack } from '@/shared/components/layout'
import { Button } from '@/shared/components/primitives'

import type { RootCauseLifecycleStatus } from '../../types'
import type { RootCauseActionName } from '../../hooks/useRootCauseActions'
import styles from './RootCauseActions.module.css'

export interface RootCauseActionsProps {
  status: RootCauseLifecycleStatus
  /** Whether this session holds the `operator` role the Gateway requires for confirm/reject/refresh. Defaults to `true` so standalone/component tests keep existing behaviour, mirroring Recommendation's `canRecordDecision`. */
  canManage?: boolean
  pendingAction: RootCauseActionName | null
  errorMessage?: string
  onConfirm: () => void
  onReject: () => void
  onRefresh: () => void
}

/**
 * Real root-cause lifecycle controls (previously a root_cause_service
 * capability with no Gateway route or frontend surface at all -- see
 * useRootCauseActions). Confirm/Reject are only meaningful while the
 * RootCause is still `identified` (root_cause_service's own lifecycle
 * rule: a terminal decision never crosses to the other terminal state);
 * Refresh is only meaningful before a final decision either, since a
 * confirmed/rejected RootCause must never be silently recalculated out
 * from under a human decision. Buttons are disabled accordingly rather
 * than hidden, so the current lifecycle state stays visible either way.
 */
export function RootCauseActions({
  status,
  canManage = true,
  pendingAction,
  errorMessage,
  onConfirm,
  onReject,
  onRefresh,
}: RootCauseActionsProps) {
  const isDecided = status !== 'identified'

  return (
    <Stack gap={3}>
      {!canManage ? (
        <AdvisoryNotice
          title="Managing root cause status requires the operator role"
          description="Your account holds read access to this investigation. Confirm, reject, and refresh will be refused by the platform; an operator or administrator can act on them."
        />
      ) : null}
      <div className={styles.actions}>
        <Button variant="primary" disabled={!canManage || isDecided} loading={pendingAction === 'confirm'} onClick={onConfirm}>
          Confirm root cause
        </Button>
        <Button variant="danger" disabled={!canManage || isDecided} loading={pendingAction === 'reject'} onClick={onReject}>
          Reject root cause
        </Button>
        <Button variant="secondary" disabled={!canManage || isDecided} loading={pendingAction === 'refresh'} onClick={onRefresh}>
          Re-run analysis
        </Button>
      </div>
      {errorMessage ? (
        <p role="alert" className={styles.error}>
          {errorMessage}
        </p>
      ) : null}
    </Stack>
  )
}
