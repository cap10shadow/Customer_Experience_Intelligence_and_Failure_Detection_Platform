import { Icon } from '@/shared/icons'
import { Stack } from '@/shared/components/layout'

import styles from './PartialFailureNotice.module.css'

export interface PartialFailureNoticeProps {
  /**
   * Human-readable notices about non-essential downstream sources that
   * were unavailable when this response was otherwise built successfully
   * (see dashboard_aggregator.py / investigation_aggregator.py's
   * essential/non-essential distinction). Renders nothing when absent or
   * empty.
   */
  warnings: string[] | undefined
}

/**
 * Surfaces the Gateway's `warnings` field. Deliberately calm, not
 * alarm-styled: a partial degradation within an otherwise-successful
 * response is not a failure -- distinct from ErrorBoundary's fallback,
 * which represents the whole section failing to load. Never fabricates
 * a warning and never suppresses one that's present.
 */
export function PartialFailureNotice({ warnings }: PartialFailureNoticeProps) {
  if (!warnings || warnings.length === 0) {
    return null
  }

  return (
    <div role="status" className={styles.container}>
      <Stack direction="row" gap={3} align="flex-start">
        <Icon name="warning" size={18} className={styles.icon} />
        <ul className={styles.list}>
          {warnings.map((warning) => (
            <li key={warning}>{warning}</li>
          ))}
        </ul>
      </Stack>
    </div>
  )
}