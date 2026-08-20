import type { ReactNode } from 'react'

import { AuthProvider } from '@/auth/context/AuthContext'
import { DatasetProvider } from '@/app/context/DatasetContext'
import { ThemeProvider } from '@/app/theme/ThemeProvider'

export interface AppProvidersProps {
  children: ReactNode
}

/**
 * Composes every application-wide context provider in one place.
 * `DatasetProvider` (docs/DECISIONS.md AD-12) sits inside `AuthProvider`
 * -- dataset selection is meaningless without a session, but (like auth)
 * must survive navigation across every workspace, so it belongs at this
 * app-wide level rather than inside the router/AppShell.
 */
export function AppProviders({ children }: AppProvidersProps) {
  return (
    <ThemeProvider>
      <AuthProvider>
        <DatasetProvider>{children}</DatasetProvider>
      </AuthProvider>
    </ThemeProvider>
  )
}
