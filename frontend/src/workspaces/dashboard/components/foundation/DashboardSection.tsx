import type { ReactNode } from 'react'

import { SectionContainer } from '@/shared/components/layout'

import styles from './DashboardSection.module.css'

export interface DashboardSectionProps {
  /** Headline -- always required, per the universal information hierarchy. */
  title: string
  /** Primary Insight -- the single most important takeaway, shown immediately under the headline. Always required. */
  insight: string
  /** Why It Matters -- business significance. Optional only because some sections carry this per-item (each card explains its own significance) rather than once for the whole section. */
  whyItMatters?: string
  headingLevel?: 2 | 3
  actions?: ReactNode
  children: ReactNode
}

/**
 * The one place the frozen Universal Information Hierarchy (Headline →
 * Primary Insight → Why It Matters → Supporting Context → Suggested Next
 * Step → Drill-down) is encoded structurally. Every top-level Dashboard
 * section (Operational Brief, Decision Summary, Investigation Entry
 * Points, Supporting Evidence) composes with this so users never need to
 * learn a different reading pattern per section -- "Supporting Context"
 * and beyond are `children`, since their shape genuinely differs per
 * section (a list of cards, a snapshot grid, ...).
 */
export function DashboardSection({ title, insight, whyItMatters, headingLevel = 2, actions, children }: DashboardSectionProps) {
  return (
    <SectionContainer title={title} description={insight} headingLevel={headingLevel} actions={actions}>
      {whyItMatters ? <p className={styles.whyItMatters}>{whyItMatters}</p> : null}
      {children}
    </SectionContainer>
  )
}
