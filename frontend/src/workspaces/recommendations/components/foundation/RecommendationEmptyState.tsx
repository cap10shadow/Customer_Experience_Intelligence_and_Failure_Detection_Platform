import { EmptyState } from '@/shared/components/feedback'
import type { IconName } from '@/shared/icons'

export interface RecommendationEmptyStateProps {
  title: string
  description: string
  icon?: IconName
}

/** Explains and reassures -- never implies malfunction, never a bare "No Data." Mirrors `InvestigationEmptyState`'s role for this workspace. */
export function RecommendationEmptyState({ title, description, icon = 'info' }: RecommendationEmptyStateProps) {
  return <EmptyState icon={icon} title={title} description={description} />
}
