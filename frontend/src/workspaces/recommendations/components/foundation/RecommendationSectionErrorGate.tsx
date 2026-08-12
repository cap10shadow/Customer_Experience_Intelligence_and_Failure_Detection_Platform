import type { ReactNode } from 'react'

export interface RecommendationSectionErrorGateProps {
  /** When present, thrown during render so the ancestor ErrorBoundary (already wrapping every Recommendation section) displays its existing fallback. Mirrors InvestigationSectionErrorGate -- see its retry caveat, which applies identically here (carried forward as a Step 7 hardening item, not fixed in Part 4). */
  error: Error | null
  children: ReactNode
}

export function RecommendationSectionErrorGate({ error, children }: RecommendationSectionErrorGateProps) {
  if (error) {
    throw error
  }
  return <>{children}</>
}
