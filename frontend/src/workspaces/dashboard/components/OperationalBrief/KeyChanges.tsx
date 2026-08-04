import { Stack } from '@/shared/components/layout'
import { Icon } from '@/shared/icons'

import { DashboardEmptyState, DashboardLoadingState, DashboardSubsectionHeading } from '../foundation'
import { TREND_ICON, type KeyChange } from '../../types'
import styles from './KeyChanges.module.css'

export interface KeyChangesProps {
  /** Deliberately empty by default -- "never invent change." A future step populates this from real deltas (complaint volume, sentiment, resolutions); until then, no change is the honest state. */
  changes?: KeyChange[]
  isLoading?: boolean
}

/** "What changed?" -- meaningful deltas only, each framed by direction so the shape (not just the fact) of the change is legible at a glance. */
export function KeyChanges({ changes = [], isLoading = false }: KeyChangesProps) {
  return (
    <Stack gap={4}>
      <DashboardSubsectionHeading title="Key changes" description="Meaningful operational changes since you last looked." />
      {isLoading ? (
        <DashboardLoadingState label="Loading key changes" />
      ) : changes.length === 0 ? (
        <DashboardEmptyState
          title="No meaningful changes"
          description="Nothing has changed significantly since your last visit."
        />
      ) : (
        <Stack gap={3}>
          {changes.map((change) => (
            <div key={change.id} className={styles.item}>
              <Icon name={TREND_ICON[change.direction]} size={18} className={styles.icon} />
              <div>
                <p className={styles.headline}>{change.headline}</p>
                <p className={styles.detail}>{change.detail}</p>
              </div>
            </div>
          ))}
        </Stack>
      )}
    </Stack>
  )
}
