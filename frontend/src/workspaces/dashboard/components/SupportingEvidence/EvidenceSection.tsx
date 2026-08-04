import { Panel } from '@/shared/components/layout'
import { Icon } from '@/shared/icons'

import { DashboardLoadingState } from '../foundation'
import type { EvidenceItem } from '../../types'
import styles from './EvidenceSection.module.css'

export interface EvidenceSectionProps {
  item: EvidenceItem
  isLoading?: boolean
}

/**
 * One future evidence widget's reserved slot -- the extension point a
 * real chart/trend component replaces later. Deliberately distinct from
 * the generic `PlaceholderCard`: it always communicates "a chart will
 * render here" via the trend icon, never a generic "coming soon."
 */
export function EvidenceSection({ item, isLoading = false }: EvidenceSectionProps) {
  return (
    <Panel className={styles.card}>
      {isLoading ? (
        <DashboardLoadingState label={`Loading ${item.headline}`} />
      ) : (
        <>
          <div className={styles.chartArea} aria-hidden="true">
            <Icon name="trendUp" size={28} />
          </div>
          <p className={styles.headline}>{item.headline}</p>
          <p className={styles.description}>{item.description}</p>
        </>
      )}
    </Panel>
  )
}
