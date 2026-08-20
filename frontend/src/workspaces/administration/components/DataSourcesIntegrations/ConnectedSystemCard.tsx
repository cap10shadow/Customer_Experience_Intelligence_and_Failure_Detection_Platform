import { Panel } from '@/shared/components/layout'
import { Card } from '@/shared/components/primitives'
import { StatusIndicator } from '@/shared/components/utility'

import { AdministrationLoadingState } from '../foundation'
import type { ConnectedSystem } from '../../types'
import styles from './ConnectedSystemCard.module.css'

export interface ConnectedSystemCardProps {
  system: ConnectedSystem
  isLoading?: boolean
}

/**
 * ADM-006: an external business system your organization integrated --
 * deliberately labeled and framed differently from `ConnectedServiceCard`
 * (Platform Overview's infrastructure dependencies). Connection Health is
 * presented with the calm `info` tone regardless of state, never a
 * critical/warning tone -- this is a descriptive fact, never live
 * monitoring, never an operational alert (per the frozen section
 * responsibility: "Never live monitoring. Never operational monitoring.
 * Never DevOps."). Built on the shared `Card` primitive as this
 * workspace's first retrofit of a hand-rolled card onto the design
 * system's shared surface (see docs/PROJECT_STATUS.md's design-system
 * gap note for the remaining, not-yet-migrated cards).
 */
export function ConnectedSystemCard({ system, isLoading = false }: ConnectedSystemCardProps) {
  if (isLoading) {
    return (
      <Panel>
        <AdministrationLoadingState label="Loading connected system" />
      </Panel>
    )
  }

  return (
    <Card title={system.name} description={<span className={styles.kind}>External business system</span>}>
      <p className={styles.description}>{system.description}</p>
      <StatusIndicator tone="info" label={`Connection health (descriptive): ${system.connectionHealth}`} />
    </Card>
  )
}
