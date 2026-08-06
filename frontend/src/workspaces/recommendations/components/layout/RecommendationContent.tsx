import type { ReactNode } from 'react'

import { Stack } from '@/shared/components/layout'

export interface RecommendationContentProps {
  children: ReactNode
}

/** The single-column, memo-style reading column -- every section in fixed order, per the frozen UX specification. */
export function RecommendationContent({ children }: RecommendationContentProps) {
  return <Stack gap={10}>{children}</Stack>
}
