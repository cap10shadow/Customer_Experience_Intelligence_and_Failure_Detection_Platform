import { Panel, Stack } from '@/shared/components/layout'
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
 * Never DevOps.").
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
    <Panel>
      <Stack gap={2}>
        <p className={styles.kind}>External business system</p>
        <p className={styles.name}>{system.name}</p>
        <p className={styles.description}>{system.description}</p>
        <StatusIndicator tone="info" label={`Connection health (descriptive): ${system.connectionHealth}`} />
      </Stack>
    </Panel>
  )
}
