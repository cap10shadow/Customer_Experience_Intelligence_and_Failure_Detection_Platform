import { Stack } from '@/shared/components/layout'
import { StatusIndicator } from '@/shared/components/utility'

import { DashboardLoadingState, DashboardSubsectionHeading } from '../foundation'
import { OPERATIONAL_STATE_LABEL, OPERATIONAL_STATE_TONE, type OperationalStateLevel } from '../../types'
import styles from './OperationalStatus.module.css'

export interface OperationalStatusProps {
  level: OperationalStateLevel
  summary: string
  /** Hybrid Time Model: the status always reflects "now", this caption just names what "now" means (e.g. "as of the last 24 hours"). */
  timeRangeLabel: string
  isLoading?: boolean
}

/**
 * "What is happening?" answered in one glance -- the first thing the
 * Dashboard shows. Tone is never conveyed by color alone: `StatusIndicator`
 * pairs a distinct icon shape with the label, and the level always maps
 * to a fixed, honest phrase (see OPERATIONAL_STATE_LABEL) rather than a
 * generated sentence -- stability is communicated confidently, not hedged.
 */
export function OperationalStatus({ level, summary, timeRangeLabel, isLoading = false }: OperationalStatusProps) {
  return (
    <Stack gap={4}>
      <DashboardSubsectionHeading title="Overall operational status" />
      {isLoading ? (
        <DashboardLoadingState label="Loading operational status" />
      ) : (
        <div className={styles.banner}>
          <StatusIndicator tone={OPERATIONAL_STATE_TONE[level]} label={OPERATIONAL_STATE_LABEL[level]} className={styles.indicator} />
          <p className={styles.summary}>{summary}</p>
          <p className={styles.caption}>Reflects {timeRangeLabel}.</p>
        </div>
      )}
    </Stack>
  )
}
