import type { ReactNode } from 'react'

import { AuthProvider } from '@/auth/context/AuthContext'
import { ThemeProvider } from '@/app/theme/ThemeProvider'

export interface AppProvidersProps {
  children: ReactNode
}

/**
 * Composes every application-wide context provider in one place.
 * `AuthProvider` (Phase 13 Batch 2) is the first provider to actually
 * use the composition point this component's own original comment
 * anticipated ("a future auth/session... provider is added here,
 * once") -- every call site (main.tsx, tests) still needs to know only
 * the one wrapper, not the full provider stack.
 */
export function AppProviders({ children }: AppProvidersProps) {
  return (
    <ThemeProvider>
      <AuthProvider>{children}</AuthProvider>
    </ThemeProvider>
  )
}
