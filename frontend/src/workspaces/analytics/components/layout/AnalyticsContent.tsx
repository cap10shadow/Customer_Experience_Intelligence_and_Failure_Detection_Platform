import type { ReactNode } from 'react'

import { Stack } from '@/shared/components/layout'

export interface AnalyticsContentProps {
  children: ReactNode
}

/** The single reading column -- every section in fixed order. */
export function AnalyticsContent({ children }: AnalyticsContentProps) {
  return <Stack gap={10}>{children}</Stack>
}
