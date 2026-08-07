import type { ReactNode } from 'react'

import { SectionContainer } from '@/shared/components/layout'

export interface AnalyticsSectionProps {
  id: string
  title: string
  description: string
  children: ReactNode
}

/**
 * All six Analytics sections compose with this so every one reads the
 * same way -- a real h2 heading plus a one-line framing description.
 * Mirrors `InvestigationSection`/`RecommendationSection` exactly; kept
 * local for the same reason both of those are: each workspace keeps its
 * own copy until a genuinely identical need justifies promotion (see
 * `FutureCapabilityPlaceholder`, promoted this step because two
 * workspaces needed the exact same component, not just the same pattern).
 */
export function AnalyticsSection({ id, title, description, children }: AnalyticsSectionProps) {
  return (
    <div id={id}>
      <SectionContainer title={title} description={description}>
        {children}
      </SectionContainer>
    </div>
  )
}
