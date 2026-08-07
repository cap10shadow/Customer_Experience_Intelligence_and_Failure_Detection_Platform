import { useContext } from 'react'

import { AnalyticsContext, type AnalyticsContextValue } from './AnalyticsContext'

export function useAnalyticsContext(): AnalyticsContextValue {
  const context = useContext(AnalyticsContext)
  if (!context) {
    throw new Error('useAnalyticsContext must be used within an AnalyticsContextProvider')
  }
  return context
}
