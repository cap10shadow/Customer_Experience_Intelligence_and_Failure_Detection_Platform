import type { ReactNode } from 'react'

import { SectionContainer } from '@/shared/components/layout'

export interface InvestigationSectionProps {
  id: string
  title: string
  description: string
  children: ReactNode
}

/**
 * The five narrative sections (Observation, Evidence, Root Cause
 * Analysis, Business Impact, Recommended Next Step) all compose with
 * this so every one reads the same way -- a real, always-h2 heading
 * (they sit directly under the workspace's h1, exactly like Dashboard's
 * top-level sections) plus a one-line framing description. Unlike
 * Dashboard's `DashboardSection`, there is no separate "why it matters"
 * slot: each Investigation section already answers one specific
 * question by design, so the framing description carries that question,
 * not a second paragraph.
 */
export function InvestigationSection({ id, title, description, children }: InvestigationSectionProps) {
  return (
    <div id={id}>
      <SectionContainer title={title} description={description}>
        {children}
      </SectionContainer>
    </div>
  )
}
