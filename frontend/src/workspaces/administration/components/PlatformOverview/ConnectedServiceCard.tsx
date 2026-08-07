import { Panel } from '@/shared/components/layout'

import { AdministrationLoadingState } from '../foundation'
import type { ConnectedService } from '../../types'
import styles from './ConnectedServiceCard.module.css'

export interface ConnectedServiceCardProps {
  service: ConnectedService
  isLoading?: boolean
}

/**
 * ADM-006: a platform infrastructure dependency -- deliberately labeled
 * and framed differently from `ConnectedSystemCard` (Data Sources &
 * Integrations' external business systems), even though both render as a
 * similar-looking card. The distinction lives in the label ("Platform
 * infrastructure dependency") and copy, not in a different visual
 * language, so the two never rely on the reader noticing a subtle style
 * difference to tell them apart.
 */
export function ConnectedServiceCard({ service, isLoading = false }: ConnectedServiceCardProps) {
  if (isLoading) {
    return (
      <Panel>
        <AdministrationLoadingState label="Loading connected service" />
      </Panel>
    )
  }

  return (
    <Panel>
      <p className={styles.kind}>Platform infrastructure dependency</p>
      <p className={styles.name}>{service.name}</p>
      <p className={styles.description}>{service.description}</p>
    </Panel>
  )
}
