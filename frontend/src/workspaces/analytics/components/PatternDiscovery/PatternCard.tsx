import { Panel, Stack } from '@/shared/components/layout'
import { Icon } from '@/shared/icons'

import { AnalyticsLoadingState } from '../foundation'
import type { PatternNarrative } from '../../types'
import styles from './PatternCard.module.css'

export interface PatternCardProps {
  pattern: PatternNarrative
  isLoading?: boolean
}

/**
 * UX-008: Headline → Narrative → Supporting Evidence -- the same
 * discipline as `TrendNarrativeCard`, deliberately, so Pattern Discovery
 * never degrades into a bare list of pattern names or a chart wall.
 */
export function PatternCard({ pattern, isLoading = false }: PatternCardProps) {
  if (isLoading) {
    return (
      <Panel>
        <AnalyticsLoadingState label="Loading pattern" />
      </Panel>
    )
  }

  return (
    <Panel>
      <Stack gap={3}>
        <p className={styles.headline}>{pattern.headline}</p>
        <p className={styles.narrative}>{pattern.narrative}</p>
        <div className={styles.evidence}>
          <div className={styles.chartArea} aria-hidden="true">
            <Icon name="investigations" size={20} />
          </div>
          <p className={styles.evidenceText}>{pattern.evidence}</p>
        </div>
      </Stack>
    </Panel>
  )
}
