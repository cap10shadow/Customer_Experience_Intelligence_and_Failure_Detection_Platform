import { ROUTE_PATHS } from '@/app/routing/routePaths'
import type { NavigationItemConfig } from '@/shared/types/navigation'

/**
 * The persistent sidebar's entire content is derived from this array --
 * it is the "future navigation extension point" the frozen architecture
 * calls for: a new workspace is added here once, and the Sidebar,
 * Breadcrumbs, and router all stay in sync automatically. Order here is
 * render order.
 *
 * Deliberately flat (no nested groups yet): the frozen architecture
 * explicitly defers secondary navigation to a future phase.
 */
export const PRIMARY_NAVIGATION: NavigationItemConfig[] = [
  {
    id: 'dashboard',
    label: 'Dashboard',
    path: ROUTE_PATHS.dashboard,
    icon: 'dashboard',
    description: 'Immediate operational awareness -- what changed, why it matters, and where to go next.',
  },
  {
    id: 'action-center',
    label: 'Action Center',
    path: ROUTE_PATHS.actionCenter,
    icon: 'actionCenter',
    description: 'Everything currently requiring operational attention.',
  },
  {
    id: 'investigations',
    label: 'Investigations',
    path: ROUTE_PATHS.investigations,
    icon: 'investigations',
    description: 'Understand operational problems from complaint through to recommendation.',
  },
  {
    id: 'recommendations',
    label: 'Recommendations',
    path: ROUTE_PATHS.recommendations,
    icon: 'recommendations',
    description: 'Recommendation lifecycle management, history, and status.',
  },
  {
    id: 'analytics',
    label: 'Analytics',
    path: ROUTE_PATHS.analytics,
    icon: 'analytics',
    description: 'Historical trends, KPIs, and strategic operational intelligence.',
  },
  {
    id: 'administration',
    label: 'Administration',
    path: ROUTE_PATHS.administration,
    icon: 'administration',
    description: 'Platform configuration -- organization, users, roles, and integrations.',
  },
]
