import { Stack } from '@/shared/components/layout'
import { StatusIndicator } from '@/shared/components/utility'

import { DashboardEmptyState, DashboardLoadingState, DashboardSubsectionHeading } from '../foundation'
import type { CriticalSituation } from '../../types'
import styles from './CriticalSituations.module.css'

export interface CriticalSituationsProps {
  /** Deliberately empty by default -- "do NOT list every incident," and this step establishes no real severity intelligence to rank situations with. An empty list is the honest default, not a placeholder gap. */
  situations?: CriticalSituation[]
  isLoading?: boolean
}

/**
 * Quality over quantity: shows only situations significant enough to
 * name individually. Absent real business intelligence to identify one,
 * the confident, honest default is "none currently" -- never a
 * manufactured entry just to fill the section.
 */
export function CriticalSituations({ situations = [], isLoading = false }: CriticalSituationsProps) {
  return (
    <Stack gap={4}>
      <DashboardSubsectionHeading
        title="Critical situations"
        description="Only situations significant enough to require immediate attention."
      />
      {isLoading ? (
        <DashboardLoadingState label="Loading critical situations" />
      ) : situations.length === 0 ? (
        <DashboardEmptyState
          title="No critical situations"
          description="Nothing currently requires immediate attention. Operations remain within expected thresholds."
        />
      ) : (
        <Stack gap={3}>
          {situations.map((situation) => (
            <div key={situation.id} className={styles.item}>
              <StatusIndicator tone="critical" label="Critical" visuallyHideLabel />
              <div>
                <p className={styles.headline}>{situation.headline}</p>
                <p className={styles.detail}>{situation.detail}</p>
              </div>
            </div>
          ))}
        </Stack>
      )}
    </Stack>
  )
}
