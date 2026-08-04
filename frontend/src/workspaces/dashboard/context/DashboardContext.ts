import { createContext } from 'react'

/**
 * The Hybrid Time Model's vocabulary. 'current' is the default and the
 * only value every section must always be able to render (the Dashboard
 * always presents the current operational state); the others exist so a
 * future time-range control has somewhere to write to without every
 * section needing new props.
 */
export type DashboardTimeRange = 'current' | '24h' | '7d' | '30d'

export const DASHBOARD_TIME_RANGE_LABELS: Record<DashboardTimeRange, string> = {
  current: 'current operational state',
  '24h': 'the last 24 hours',
  '7d': 'the last 7 days',
  '30d': 'the last 30 days',
}

/**
 * One shared operational scope for the entire Dashboard -- Region,
 * Business Unit, Product Scope, and User Scope are all future filters;
 * `null` means "all" (no scope narrowing), which is the only state this
 * step ever renders. The shape exists now so a future filter bar has a
 * single place to write to, and every section already reads from here
 * rather than local state.
 */
export interface DashboardGlobalContextValue {
  timeRange: DashboardTimeRange
  region: string | null
  businessUnit: string | null
  productScope: string | null
  userScope: string | null
}

export interface DashboardContextValue extends DashboardGlobalContextValue {
  setTimeRange: (timeRange: DashboardTimeRange) => void
  setRegion: (region: string | null) => void
  setBusinessUnit: (businessUnit: string | null) => void
}

export const DEFAULT_DASHBOARD_CONTEXT: DashboardGlobalContextValue = {
  timeRange: 'current',
  region: null,
  businessUnit: null,
  productScope: null,
  userScope: null,
}

export const DashboardContext = createContext<DashboardContextValue | undefined>(undefined)
