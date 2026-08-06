import type { ReactNode } from 'react'

import { Stack } from '@/shared/components/layout'

export interface InvestigationContentProps {
  children: ReactNode
}

/** The main reading column -- every narrative section and the closing Recommendation transition, in fixed order. */
export function InvestigationContent({ children }: InvestigationContentProps) {
  return <Stack gap={10}>{children}</Stack>
}
