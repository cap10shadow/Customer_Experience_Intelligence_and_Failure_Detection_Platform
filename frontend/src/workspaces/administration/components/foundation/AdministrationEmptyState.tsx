import { EmptyState } from '@/shared/components/feedback'
import type { IconName } from '@/shared/icons'

export interface AdministrationEmptyStateProps {
  title: string
  description: string
  icon?: IconName
}

/** Explains and reassures -- never "No Data" or "Empty." A quiet Administration section (no integrations connected yet, no audit entries on a fresh instance) is a normal, expected state, not a malfunction. */
export function AdministrationEmptyState({ title, description, icon = 'info' }: AdministrationEmptyStateProps) {
  return <EmptyState icon={icon} title={title} description={description} />
}
