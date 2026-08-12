import type { ReactNode } from 'react'

export interface AdministrationSectionErrorGateProps {
  /** When present, thrown during render so the ancestor ErrorBoundary displays its existing fallback -- mirrors DashboardSectionErrorGate/InvestigationSectionErrorGate exactly. */
  error: Error | null
  children: ReactNode
}

export function AdministrationSectionErrorGate({ error, children }: AdministrationSectionErrorGateProps) {
  if (error) {
    throw error
  }
  return <>{children}</>
}
