import type { ReactNode } from 'react'

export interface AnalyticsSectionErrorGateProps {
  /** When present, thrown during render so the ancestor ErrorBoundary (already wrapping every Analytics section) displays its existing fallback. Mirrors DashboardSectionErrorGate/InvestigationSectionErrorGate/RecommendationSectionErrorGate -- see their retry caveat, which applies identically here (carried forward as a Part 7 hardening item, not fixed in Part 5). */
  error: Error | null
  children: ReactNode
}

export function AnalyticsSectionErrorGate({ error, children }: AnalyticsSectionErrorGateProps) {
  if (error) {
    throw error
  }
  return <>{children}</>
}
