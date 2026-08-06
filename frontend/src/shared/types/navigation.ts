import type { IconName } from '@/shared/icons'

/**
 * The five frozen operational workspaces. Adding a workspace means adding
 * one id here, one route, and one navigation config entry -- never
 * renaming or repurposing an existing one (navigation must remain
 * stable and predictable across phases). Action Center was retired as a
 * standalone workspace per the approved workspace refinement; its
 * decision-and-action responsibility now belongs to Recommendations --
 * see `docs/DECISIONS.md` (FE-001).
 */
export type WorkspaceId =
  | 'dashboard'
  | 'investigations'
  | 'recommendations'
  | 'analytics'
  | 'administration'

export interface NavigationItemConfig {
  id: WorkspaceId
  /** User-facing label -- describes the goal the workspace serves, never the backing service. */
  label: string
  path: string
  icon: IconName
  /** Short description surfaced to assistive tech and future tooltips. */
  description: string
}

export interface BreadcrumbSegment {
  label: string
  path?: string
}
