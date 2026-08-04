import { Grid, Stack } from '@/shared/components/layout'
import { Icon } from '@/shared/icons'
import { StatusIndicator } from '@/shared/components/utility'

import { DashboardLoadingState, DashboardSubsectionHeading } from '../foundation'
import { OPERATIONAL_STATE_TONE, TREND_ICON, type HealthIndicator } from '../../types'
import styles from './OperationalHealthSnapshot.module.css'

export interface OperationalHealthSnapshotProps {
  indicators: HealthIndicator[]
  isLoading?: boolean
}

/**
 * "How healthy is the operation, at a glance?" -- concise indicators
 * only, never the detailed analytics Supporting Evidence owns. Always
 * renders (a snapshot has no meaningful "empty" state, unlike Critical
 * Situations or Key Changes): every indicator always has some value.
 */
export function OperationalHealthSnapshot({ indicators, isLoading = false }: OperationalHealthSnapshotProps) {
  return (
    <Stack gap={4}>
      <DashboardSubsectionHeading title="Operational health snapshot" />
      {isLoading ? (
        <DashboardLoadingState label="Loading operational health snapshot" />
      ) : (
        <Grid minColumnWidth={200}>
          {indicators.map((indicator) => (
            <div key={indicator.id} className={styles.indicator}>
              <p className={styles.label}>{indicator.label}</p>
              <StatusIndicator tone={OPERATIONAL_STATE_TONE[indicator.level]} label={indicator.detail} />
              <span className={styles.trend}>
                <Icon name={TREND_ICON[indicator.trend]} size={14} />
              </span>
            </div>
          ))}
        </Grid>
      )}
    </Stack>
  )
}
