import { Panel } from '@/shared/components/layout'

import { AdministrationLoadingState } from '../foundation'
import type { PlatformOverviewFact } from '../../types'
import styles from './FactCard.module.css'

export interface FactCardProps {
  fact: PlatformOverviewFact
  isLoading?: boolean
}

/** One descriptive platform fact -- reference-register, scanned not read. Deliberately no action, no recommendation, matching Platform Overview's "descriptive only" purpose. */
export function FactCard({ fact, isLoading = false }: FactCardProps) {
  if (isLoading) {
    return (
      <Panel>
        <AdministrationLoadingState label="Loading platform fact" />
      </Panel>
    )
  }

  return (
    <Panel>
      <p className={styles.label}>{fact.label}</p>
      <p className={styles.value}>{fact.value}</p>
    </Panel>
  )
}
