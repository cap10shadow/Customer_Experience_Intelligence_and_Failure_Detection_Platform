import { Panel, Stack } from '@/shared/components/layout'

import { AdministrationLoadingState } from '../foundation'
import type { ConfigurationItem } from '../../types'
import styles from './ConfigurationItemCard.module.css'

export interface ReadOnlyConfigurationItemCardProps {
  item: ConfigurationItem
  isLoading?: boolean
}

/**
 * Read-only rendering of one real Business Impact configuration value
 * (Step 7.X G-05) -- same ADM-002 field order as `ConfigurationItemCard`
 * (what it is -> what it governs -> current value), but deliberately
 * carries no edit button, no save affordance, and no
 * `AdministrationContext` wiring: these values are current, informational
 * snapshots of the live engine, never presented as editable. A distinct
 * component from `ConfigurationItemCard` rather than a conditional inside
 * it, so "no mutation control exists" is true by construction, not by a
 * prop that could be flipped.
 */
export function ReadOnlyConfigurationItemCard({ item, isLoading = false }: ReadOnlyConfigurationItemCardProps) {
  if (isLoading) {
    return (
      <Panel>
        <AdministrationLoadingState label="Loading configuration item" />
      </Panel>
    )
  }

  return (
    <Panel className={styles.item}>
      <Stack gap={3}>
        <div>
          <p className={styles.name}>{item.name}</p>
          <p className={styles.whatItIs}>{item.whatItIs}</p>
        </div>

        <p className={styles.governs}>
          <span className={styles.governsLabel}>Governs</span> {item.governs}
        </p>

        <div className={styles.valueRow}>
          <span className={styles.valueLabel}>Current value (read-only)</span>
          <output className={styles.valueInput}>{item.currentValue}</output>
        </div>
      </Stack>
    </Panel>
  )
}
