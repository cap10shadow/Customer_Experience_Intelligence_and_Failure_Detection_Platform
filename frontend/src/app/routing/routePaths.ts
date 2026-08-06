/**
 * Centralized route paths -- the single source of truth every link,
 * redirect, and route definition references. Never hard-code a path
 * string anywhere else; import from here so a future path change is a
 * one-line edit, not a repository-wide find/replace.
 */
export const ROUTE_PATHS = {
  dashboard: '/',
  investigations: '/investigations',
  recommendations: '/recommendations',
  analytics: '/analytics',
  administration: '/administration',
} as const

export type RoutePathKey = keyof typeof ROUTE_PATHS
