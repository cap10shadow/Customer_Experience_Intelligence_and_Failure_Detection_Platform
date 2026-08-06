import { EmptyState } from '@/shared/components/feedback'
import type { IconName } from '@/shared/icons'

export interface InvestigationEmptyStateProps {
  title: string
  /** Should cover both why nothing is available yet and what to expect -- never a bare "No Data." */
  description: string
  icon?: IconName
}

/**
 * Investigation's empty states explain absence, they don't just declare
 * it: "why nothing is available" and "what happens next" both belong in
 * `description`. Defaults to the 'info' icon (this stage genuinely
 * hasn't run yet) rather than Dashboard's 'check' (confirmed healthy) --
 * the two workspaces' empty states mean different things and
 * deliberately don't share a default.
 */
export function InvestigationEmptyState({ title, description, icon = 'info' }: InvestigationEmptyStateProps) {
  return <EmptyState icon={icon} title={title} description={description} />
}
