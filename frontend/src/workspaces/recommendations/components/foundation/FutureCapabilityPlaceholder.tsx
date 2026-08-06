import { Icon, type IconName } from '@/shared/icons'
import { Stack } from '@/shared/components/layout'

import { RecommendationLoadingState } from './RecommendationLoadingState'
import styles from './FutureCapabilityPlaceholder.module.css'

export interface FutureCapabilityPlaceholderProps {
  title: string
  description: string
  icon?: IconName
  isLoading?: boolean
}

/**
 * UX-003: Alternative Options is not "empty" -- the Recommendation
 * Decision Engine does not yet preserve alternatives it considered and
 * did not select (see `docs/DECISIONS.md`, REC-001), so there is
 * nothing to compare yet, full stop. That is a future capability, not
 * an absence of data for something the platform already computes.
 * Deliberately distinct from `RecommendationEmptyState`: never says
 * "No Data" or "Empty," and is framed entirely in terms of what's
 * coming, not what's missing.
 *
 * `isLoading` is handled here, inside the same `.panel` container both
 * states share -- matching every other card in this workspace (Overview,
 * Rationale, Outcome, Risk, Decision) so the dashed-border shape never
 * shifts between loading and resolved content.
 */
export function FutureCapabilityPlaceholder({ title, description, icon = 'info', isLoading = false }: FutureCapabilityPlaceholderProps) {
  return (
    <div className={styles.panel}>
      {isLoading ? (
        <RecommendationLoadingState label="Loading alternative options" />
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
