import { Stack } from '@/shared/components/layout'

import { DashboardEmptyState, DashboardLoadingState, DashboardSubsectionHeading } from '../foundation'
import type { FocusArea } from '../../types'
import styles from './RecommendedFocus.module.css'

export interface RecommendedFocusProps {
  /** Deliberately empty by default -- guidance only exists once a genuine focus area is identified; absent one, "keep doing what you're doing" is the honest, confident answer. */
  focusAreas?: FocusArea[]
  isLoading?: boolean
}

/** "What should I focus on?" -- guides attention, never issues instructions. */
export function RecommendedFocus({ focusAreas = [], isLoading = false }: RecommendedFocusProps) {
  return (
    <Stack gap={4}>
      <DashboardSubsectionHeading title="Recommended focus" description="Where your attention is most valuable right now." />
      {isLoading ? (
        <DashboardLoadingState label="Loading recommended focus" />
      ) : focusAreas.length === 0 ? (
        <DashboardEmptyState
          title="No focus area required"
          description="Customer experience remains stable. Continue routine monitoring."
        />
      ) : (
        <Stack gap={3}>
          {focusAreas.map((focus) => (
            <div key={focus.id} className={styles.item}>
              <p className={styles.headline}>{focus.headline}</p>
              <p className={styles.reason}>{focus.reason}</p>
            </div>
          ))}
        </Stack>
      )}
    </Stack>
  )
}
