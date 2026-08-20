import type { ReactNode } from 'react'

import { SectionContainer } from '@/shared/components/layout'
import { classNames } from '@/shared/utilities/classNames'

import type { AdministrationRegister } from '../../context'
import styles from './AdministrationSection.module.css'

export interface AdministrationSectionProps {
  id: string
  title: string
  description: string
  /** ADM-005: a subtle, presentation-only rhythm cue for which of the three registers (State / Configuration / Record) this section belongs to -- never a navigation grouping, never a new landmark. */
  register: AdministrationRegister
  /**
   * A small "Live"/"Not Yet Operational" indicator next to the section
   * title (see `AdministrationStatusBadge`) -- makes the real/placeholder
   * distinction each section's own `AdvisoryNotice` already discloses in
   * prose scannable at a glance, rather than requiring a read of every
   * section's body to know which two of six are backed by a real Gateway
   * capability.
   */
  statusBadge?: ReactNode
  children: ReactNode
}

/**
 * All six Administration sections compose with this so every one reads
 * the same way -- a real h2 heading plus a one-line framing description.
 * Mirrors `InvestigationSection`/`RecommendationSection`/`AnalyticsSection`
 * exactly; kept local for the same "avoid premature shared extraction"
 * reason each of those already documents. The `register` prop drives only
 * spacing (see `AdministrationSection.module.css`) -- it never changes
 * heading level, landmark structure, or navigation.
 */
export function AdministrationSection({ id, title, description, register, statusBadge, children }: AdministrationSectionProps) {
  return (
    <div id={id} data-register={register} className={classNames(styles.section, styles[register])}>
      <SectionContainer title={title} description={description} actions={statusBadge}>
        {children}
      </SectionContainer>
    </div>
  )
}
