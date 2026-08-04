import { useCallback, useMemo, useState, type ReactNode } from 'react'

import {
  DashboardContext,
  DEFAULT_DASHBOARD_CONTEXT,
  type DashboardTimeRange,
} from './DashboardContext'

export interface DashboardContextProviderProps {
  children: ReactNode
}

/**
 * The single owner of Dashboard-wide scope (Global Dashboard Context).
 * Every section reads from here instead of holding its own scope, so
 * two sections can never disagree about what time range or region
 * they're showing. No control in this step calls the setters -- they
 * exist so a future filter bar changes one provider, not every section.
 */
export function DashboardContextProvider({ children }: DashboardContextProviderProps) {
  const [timeRange, setTimeRange] = useState<DashboardTimeRange>(DEFAULT_DASHBOARD_CONTEXT.timeRange)
  const [region, setRegion] = useState<string | null>(DEFAULT_DASHBOARD_CONTEXT.region)
  const [businessUnit, setBusinessUnit] = useState<string | null>(DEFAULT_DASHBOARD_CONTEXT.businessUnit)

  const setTimeRangeCallback = useCallback((next: DashboardTimeRange) => setTimeRange(next), [])
  const setRegionCallback = useCallback((next: string | null) => setRegion(next), [])
  const setBusinessUnitCallback = useCallback((next: string | null) => setBusinessUnit(next), [])

  const value = useMemo(
    () => ({
      timeRange,
      region,
      businessUnit,
      productScope: DEFAULT_DASHBOARD_CONTEXT.productScope,
      userScope: DEFAULT_DASHBOARD_CONTEXT.userScope,
      setTimeRange: setTimeRangeCallback,
      setRegion: setRegionCallback,
      setBusinessUnit: setBusinessUnitCallback,
    }),
    [timeRange, region, businessUnit, setTimeRangeCallback, setRegionCallback, setBusinessUnitCallback],
  )

  return <DashboardContext.Provider value={value}>{children}</DashboardContext.Provider>
}
