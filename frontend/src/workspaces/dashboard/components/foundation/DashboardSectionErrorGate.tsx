import type { ReactNode } from 'react'

export interface DashboardSectionErrorGateProps {
  /** When present, thrown during render so the ancestor ErrorBoundary (already wrapping every Dashboard section) displays its existing fallback -- this is the only error-presentation mechanism this codebase has today; see DashboardWorkspace's doc comment for the retry caveat. */
  error: Error | null
  children: ReactNode
}

export function DashboardSectionErrorGate({ error, children }: DashboardSectionErrorGateProps) {
  if (error) {
    throw error
  }
  return <>{children}</>
}
