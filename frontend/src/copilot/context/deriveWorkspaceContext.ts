import { ROUTE_PATHS } from '@/app/routing/routePaths'

import type { CopilotWorkspaceContext } from '../api/types'

/**
 * Derives the Copilot launch context (architecture §4.1) purely from the
 * current route -- `workspace`, and `incidentId`/`recommendationId` when
 * the URL's own dynamic segment carries one (`/investigations/:incidentId`,
 * `/recommendations/:recommendationId`, mirroring `routePaths.ts`'s own
 * `ROUTE_TEMPLATES`).
 *
 * Deliberately does not read `DashboardContext`/`AnalyticsContext`/etc to
 * populate `filters`/`timeRange`: the Copilot component is mounted once at
 * the `AppShell` level (§4, "mounted once, application-wide"), a sibling
 * of the routed `<Outlet/>`, not a descendant of any workspace's own
 * `XContextProvider` -- so those hooks are not reachable here without
 * either prop-drilling context values up through every workspace or
 * introducing a new duplicate global context, both of which the Batch 5
 * implementation prompt explicitly discourages ("do not duplicate all
 * five context models into one new global context unless the frozen
 * architecture explicitly requires it"). `filters`/`timeRange` are
 * therefore omitted entirely (both fields are optional on the frozen
 * `WorkspaceContext` contract) rather than fabricated or guessed -- see
 * the Batch 5 implementation report's gaps section.
 */
export function deriveWorkspaceContext(pathname: string): CopilotWorkspaceContext {
  const investigationMatch = pathname.match(/^\/investigations\/([^/]+)/)
  if (investigationMatch) {
    return { workspace: 'investigations', incidentId: decodeURIComponent(investigationMatch[1]) }
  }
  if (pathname.startsWith(ROUTE_PATHS.investigations)) {
    return { workspace: 'investigations' }
  }

  const recommendationMatch = pathname.match(/^\/recommendations\/([^/]+)/)
  if (recommendationMatch) {
    return { workspace: 'recommendations', recommendationId: decodeURIComponent(recommendationMatch[1]) }
  }
  if (pathname.startsWith(ROUTE_PATHS.recommendations)) {
    return { workspace: 'recommendations' }
  }

  if (pathname.startsWith(ROUTE_PATHS.analytics)) {
    return { workspace: 'analytics' }
  }
  if (pathname.startsWith(ROUTE_PATHS.administration)) {
    return { workspace: 'administration' }
  }

  return { workspace: 'dashboard' }
}
