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
 * they're showing. No control in this step calls any of the five
 * setters -- they exist so a future filter bar changes one provider,
 * not every section. All four scope dimensions (region, businessUnit,
 * productScope, userScope) are held symmetrically: none is real
 * filtering yet (the Gateway rejects any non-null value today, see
 * dashboard.py), this is presentation-state plumbing only.
 */
export function DashboardContextProvider({ children }: DashboardContextProviderProps) {
  const [timeRange, setTimeRange] = useState<DashboardTimeRange>(DEFAULT_DASHBOARD_CONTEXT.timeRange)
  const [region, setRegion] = useState<string | null>(DEFAULT_DASHBOARD_CONTEXT.region)
  const [businessUnit, setBusinessUnit] = useState<string | null>(DEFAULT_DASHBOARD_CONTEXT.businessUnit)
  const [productScope, setProductScope] = useState<string | null>(DEFAULT_DASHBOARD_CONTEXT.productScope)
  const [userScope, setUserScope] = useState<string | null>(DEFAULT_DASHBOARD_CONTEXT.userScope)

  const setTimeRangeCallback = useCallback((next: DashboardTimeRange) => setTimeRange(next), [])
  const setRegionCallback = useCallback((next: string | null) => setRegion(next), [])
  const setBusinessUnitCallback = useCallback((next: string | null) => setBusinessUnit(next), [])
  const setProductScopeCallback = useCallback((next: string | null) => setProductScope(next), [])
  const setUserScopeCallback = useCallback((next: string | null) => setUserScope(next), [])

  const value = useMemo(
    () => ({
      timeRange,
      region,
      businessUnit,
      productScope,
      userScope,
      setTimeRange: setTimeRangeCallback,
      setRegion: setRegionCallback,
      setBusinessUnit: setBusinessUnitCallback,
      setProductScope: setProductScopeCallback,
      setUserScope: setUserScopeCallback,
    }),
    [
      timeRange,
      region,
      businessUnit,
      productScope,
      userScope,
      setTimeRangeCallback,
      setRegionCallback,
      setBusinessUnitCallback,
      setProductScopeCallback,
      setUserScopeCallback,
    ],
  )

  return <DashboardContext.Provider value={value}>{children}</DashboardContext.Provider>
}
