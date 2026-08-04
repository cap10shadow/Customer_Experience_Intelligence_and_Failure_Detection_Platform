import type { ReactNode } from 'react'

import { EmptyState } from '@/shared/components/feedback'

export interface DashboardEmptyStateProps {
  title: string
  description?: string
  action?: ReactNode
}

/**
 * The Dashboard's one confident empty state: an empty section is not a
 * failure and is never presented as one. Always uses the 'check' icon
 * (stability, not "nothing found") -- per the Stability Philosophy,
 * callers must pass confident copy ("Operations Healthy", "No
 * operational decisions require attention"), never "No Data."
 */
export function DashboardEmptyState({ title, description, action }: DashboardEmptyStateProps) {
  return <EmptyState icon="check" title={title} description={description} action={action} />
}
