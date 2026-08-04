import { useContext } from 'react'

import { DashboardContext, type DashboardContextValue } from './DashboardContext'

/** Every Dashboard section calls this instead of holding its own scope -- see DashboardContextProvider. */
export function useDashboardContext(): DashboardContextValue {
  const context = useContext(DashboardContext)
  if (!context) {
    throw new Error('useDashboardContext must be used within a DashboardContextProvider')
  }
  return context
}
