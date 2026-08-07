import type { ReactNode } from 'react'

import { Stack } from '@/shared/components/layout'

export interface AdministrationContentProps {
  children: ReactNode
}

/**
 * The single reading column -- every section in fixed order. The base
 * gap is uniform; ADM-005's extra rhythm at register transitions is
 * layered on top by each `AdministrationSection` itself (see
 * `AdministrationSection.module.css`), not by this component.
 */
export function AdministrationContent({ children }: AdministrationContentProps) {
  return <Stack gap={10}>{children}</Stack>
}
