import { Grid } from '@/shared/components/layout'

import { useInvestigationContext } from '../../context'
import type { EvidenceItem } from '../../types'
import { EvidenceCard } from './EvidenceCard'
import styles from './EvidenceGroup.module.css'

export interface EvidenceGroupProps {
  items: EvidenceItem[]
  /** How many cards show before the group must be expanded -- progressive disclosure (Product Experience Guide, Principle 5), not pagination. */
  collapsedCount?: number
  isLoading?: boolean
}

/**
 * Groups evidence cards with a real expand/collapse driven by
 * `InvestigationContext.expandedSections` -- the architectural
 * mechanism the frozen design calls out, demonstrated here rather than
 * left unused. Reuses the 'evidence' section id as the group's expand
 * key since this step has exactly one evidence group; a future step
 * with multiple groups would key each independently.
 */
export function EvidenceGroup({ items, collapsedCount = 2, isLoading = false }: EvidenceGroupProps) {
  const { expandedSections, toggleSectionExpanded } = useInvestigationContext()
  const isExpanded = expandedSections.has('evidence')
  const visibleItems = isExpanded ? items : items.slice(0, collapsedCount)
  const hiddenCount = items.length - visibleItems.length

  return (
    <div>
      <Grid minColumnWidth={240}>
        {visibleItems.map((item) => (
          <EvidenceCard key={item.id} evidence={item} isLoading={isLoading} />
        ))}
      </Grid>
      {!isLoading && hiddenCount > 0 ? (
        <button type="button" className={styles.expandToggle} onClick={() => toggleSectionExpanded('evidence')}>
          Show {hiddenCount} more piece{hiddenCount === 1 ? '' : 's'} of evidence
        </button>
      ) : null}
      {!isLoading && isExpanded && items.length > collapsedCount ? (
        <button type="button" className={styles.expandToggle} onClick={() => toggleSectionExpanded('evidence')}>
          Show fewer
        </button>
      ) : null}
    </div>
  )
}
