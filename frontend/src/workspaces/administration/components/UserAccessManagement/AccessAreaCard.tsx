import { Panel } from '@/shared/components/layout'

import { AdministrationLoadingState } from '../foundation'
import type { AccessArea } from '../../types'
import styles from './AccessAreaCard.module.css'

export interface AccessAreaCardProps {
  area: AccessArea
  isLoading?: boolean
}

/**
 * One governed area of "who can use the platform" (Users, Roles,
 * Permission groups, Authentication provider, Access policies) --
 * deliberately identity/permission facts only. Never user analytics,
 * activity monitoring, or behavioral analysis, per the frozen section
 * responsibility.
 */
export function AccessAreaCard({ area, isLoading = false }: AccessAreaCardProps) {
  if (isLoading) {
    return (
      <Panel>
        <AdministrationLoadingState label="Loading access area" />
      </Panel>
    )
  }

  return (
    <Panel>
      <p className={styles.label}>{area.label}</p>
      <p className={styles.summary}>{area.summary}</p>
    </Panel>
  )
}
