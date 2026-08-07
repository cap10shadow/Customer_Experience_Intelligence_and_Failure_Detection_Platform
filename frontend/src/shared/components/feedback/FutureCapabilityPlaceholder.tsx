import { Icon, type IconName } from '@/shared/icons'
import { Stack } from '@/shared/components/layout'

import { Skeleton } from './Skeleton'
import styles from './FutureCapabilityPlaceholder.module.css'

export interface FutureCapabilityPlaceholderProps {
  title: string
  description: string
  icon?: IconName
  isLoading?: boolean
  /** Announced to screen readers while loading -- keep specific (e.g. "Loading alternative options"). */
  loadingLabel?: string
}

/**
 * Marks a section that is architecturally real but has no capability to
 * draw on yet -- distinct from an empty result (`EmptyState`): the
 * platform doesn't yet compute anything for this section at all, so
 * there is nothing to be "empty." Never says "No Data" or "Empty";
 * always frames itself in terms of what's coming, not what's missing.
 * Promoted here from the Recommendation workspace (Phase 10 Step 4's
 * Alternative Options) once Analytics (Step 5's Recommendation
 * Effectiveness) needed the identical component -- reused, not
 * reimplemented, per the frozen instruction that introduced this move.
 *
 * `isLoading` renders inside the same dashed `.panel` container the
 * resolved content uses, so the shape never shifts between loading and
 * resolved states.
 */
export function FutureCapabilityPlaceholder({
  title,
  description,
  icon = 'info',
  isLoading = false,
  loadingLabel = 'Loading',
}: FutureCapabilityPlaceholderProps) {
  return (
    <div className={styles.panel}>
      {isLoading ? (
        <div aria-busy="true" aria-live="polite">
          <span className="visually-hidden">{loadingLabel}</span>
          <Stack gap={2}>
            <Skeleton width="55%" height={14} />
            <Skeleton width="90%" height={12} />
            <Skeleton width="70%" height={12} />
          </Stack>
        </div>
      ) : (
        <Stack direction="row" gap={3} align="flex-start">
          <Icon name={icon} size={24} className={styles.icon} />
          <div>
            <p className={styles.title}>{title}</p>
            <p className={styles.description}>{description}</p>
          </div>
        </Stack>
      )}
    </div>
  )
}
