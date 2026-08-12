import type { ReactNode } from 'react'

export interface InvestigationSectionErrorGateProps {
  /** When present, thrown during render so the ancestor ErrorBoundary (already wrapping every Investigation section) displays its existing fallback. Mirrors Dashboard's DashboardSectionErrorGate -- see its retry caveat, which applies identically here (carried forward as a Step 7 hardening item, not fixed in Part 3). */
  error: Error | null
  children: ReactNode
}

export function InvestigationSectionErrorGate({ error, children }: InvestigationSectionErrorGateProps) {
  if (error) {
    throw error
  }
  return <>{children}</>
}
