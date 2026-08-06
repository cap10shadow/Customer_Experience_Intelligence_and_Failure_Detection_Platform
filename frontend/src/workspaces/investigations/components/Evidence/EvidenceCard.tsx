import { Panel } from '@/shared/components/layout'
import { Badge } from '@/shared/components/utility'
import { classNames } from '@/shared/utilities/classNames'

import { InvestigationLoadingState } from '../foundation'
import { useInvestigationContext } from '../../context'
import type { EvidenceItem } from '../../types'
import styles from './EvidenceCard.module.css'

export interface EvidenceCardProps {
  evidence: EvidenceItem
  isLoading?: boolean
}

/**
 * One piece of the Evidence Chain (ARB-006) -- always attributed to the
 * pipeline stage that produced it, never presented as an unsourced
 * claim. Selecting a card records it in `InvestigationContext` as the
 * currently-referenced evidence; nothing downstream consumes that
 * selection yet, but the mechanism -- one investigation-wide notion of
 * "which evidence is the user looking at" -- is the architectural point.
 */
export function EvidenceCard({ evidence, isLoading = false }: EvidenceCardProps) {
  const { selectedEvidenceId, selectEvidence } = useInvestigationContext()
  const isSelected = selectedEvidenceId === evidence.id

  if (isLoading) {
    return (
      <Panel as="article">
        <InvestigationLoadingState label="Loading evidence" />
      </Panel>
    )
  }

  return (
    <Panel as="article" className={classNames(styles.card, isSelected && styles.selected)}>
      <button
        type="button"
        className={styles.trigger}
        onClick={() => selectEvidence(isSelected ? null : evidence.id)}
        aria-pressed={isSelected}
      >
        <Badge tone="neutral">{evidence.source}</Badge>
        <p className={styles.headline}>{evidence.headline}</p>
        <p className={styles.detail}>{evidence.detail}</p>
      </button>
    </Panel>
  )
}
