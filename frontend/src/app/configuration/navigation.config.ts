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
    id: 'ingestion',
    label: 'Data',
    path: ROUTE_PATHS.ingestion,
    icon: 'upload',
    description: 'Bring complaint records into the platform -- the entry point into the operational intelligence lifecycle.',
  },
  {
    id: 'dashboard',
    label: 'Dashboard',
    path: ROUTE_PATHS.dashboard,
    icon: 'dashboard',
    description: 'Immediate operational awareness -- what changed, why it matters, and where to go next.',
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
