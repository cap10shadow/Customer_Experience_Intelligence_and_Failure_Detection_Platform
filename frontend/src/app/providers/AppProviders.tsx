import type { ReactNode } from 'react'

import { ThemeProvider } from '@/app/theme/ThemeProvider'

export interface AppProvidersProps {
  children: ReactNode
}

/**
 * Composes every application-wide context provider in one place. This
 * phase only has `ThemeProvider` to compose, but the composition point
 * itself is the architectural requirement -- a future auth/session or
 * data-fetching provider is added here, once, rather than every call
 * site (main.tsx, tests) needing to know the full provider stack.
 */
export function AppProviders({ children }: AppProvidersProps) {
  return <ThemeProvider>{children}</ThemeProvider>
}
