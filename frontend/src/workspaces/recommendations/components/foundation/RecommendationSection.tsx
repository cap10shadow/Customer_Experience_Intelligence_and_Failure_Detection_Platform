import type { ReactNode } from 'react'

import { SectionContainer } from '@/shared/components/layout'

export interface RecommendationSectionProps {
  id: string
  title: string
  description: string
  children: ReactNode
}

/**
 * All seven Recommendation sections compose with this so every one
 * reads the same way -- a real h2 heading plus a one-line framing
 * description, matching the memo-style, single-column reading flow the
 * frozen UX specification calls for. Mirrors `InvestigationSection`
 * exactly (same role, same shape); kept local rather than shared since
 * only two workspaces need it so far and each already keeps its own
 * copy per the "avoid premature shared extraction" principle.
 */
export function RecommendationSection({ id, title, description, children }: RecommendationSectionProps) {
  return (
    <div id={id}>
      <SectionContainer title={title} description={description}>
        {children}
      </SectionContainer>
    </div>
  )
}
