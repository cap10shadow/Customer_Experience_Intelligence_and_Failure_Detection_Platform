/**
 * Centralized route paths -- the single source of truth every link,
 * redirect, and route definition references. Never hard-code a path
 * string anywhere else; import from here so a future path change is a
 * one-line edit, not a repository-wide find/replace.
 */
export const ROUTE_PATHS = {
  dashboard: '/',
  ingestion: '/data',
  investigations: '/investigations',
  recommendations: '/recommendations',
  analytics: '/analytics',
  administration: '/administration',
  // Phase 13 Batch 2 (AD-6): the one anonymous-accessible route in the
  // frontend router -- outside AppShell, so it never renders the
  // sidebar/top bar chrome a signed-out visitor shouldn't see.
  login: '/login',
} as const

export type RoutePathKey = keyof typeof ROUTE_PATHS

/**
 * Route *templates* (react-router path patterns) for workspaces with a
 * dynamic segment -- kept separate from ROUTE_PATHS so existing literal
 * uses of `ROUTE_PATHS.investigations` (illustrative defaults, standalone
 * component tests) keep resolving to the bare `/investigations` string;
 * only AppRouter's route registration needs the `:incidentId` pattern.
 */
export const ROUTE_TEMPLATES = {
  investigation: `${ROUTE_PATHS.investigations}/:incidentId`,
  recommendation: `${ROUTE_PATHS.recommendations}/:recommendationId`,
} as const

/** Builds a real, navigable Investigation link for a given Incident -- the canonical way to link into Investigations (never a `?incidentId=` query string). */
export function buildInvestigationPath(incidentId: string): string {
  return `${ROUTE_PATHS.investigations}/${encodeURIComponent(incidentId)}`
}

/** Builds a real, navigable Recommendation link for a given recommendation -- the canonical way to link into Recommendations (never a `?recommendationId=` query string). */
export function buildRecommendationPath(recommendationId: string): string {
  return `${ROUTE_PATHS.recommendations}/${encodeURIComponent(recommendationId)}`
}
