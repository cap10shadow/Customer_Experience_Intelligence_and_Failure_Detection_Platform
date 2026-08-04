import type { IconName } from '@/shared/icons'

/**
 * The six frozen operational workspaces. Adding a workspace means adding
 * one id here, one route, and one navigation config entry -- never
 * renaming or repurposing an existing one (navigation must remain
 * stable and predictable across phases).
 */
export type WorkspaceId =
  | 'dashboard'
  | 'action-center'
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
