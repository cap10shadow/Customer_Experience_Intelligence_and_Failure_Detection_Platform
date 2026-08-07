import { EmptyState } from '@/shared/components/feedback'
import type { IconName } from '@/shared/icons'

export interface AnalyticsEmptyStateProps {
  title: string
  description: string
  icon?: IconName
}

/** Explains, never "No Analytics" -- organizational learning grows as operational history accumulates; an empty section says so, it doesn't imply malfunction. */
export function AnalyticsEmptyState({ title, description, icon = 'info' }: AnalyticsEmptyStateProps) {
  return <EmptyState icon={icon} title={title} description={description} />
}
