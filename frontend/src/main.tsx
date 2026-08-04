import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { RouterProvider } from 'react-router-dom'

import { AppProviders } from '@/app/providers/AppProviders'
import { router } from '@/app/routing/AppRouter'
import { ErrorBoundary } from '@/shared/components/feedback'
import '@/app/theme/index.css'

// Global boundary: catches failures outside any single workspace (the
// router itself, providers, or the app shell/sidebar/top bar). It is
// distinct from WorkspaceLayout's per-route boundary, which isolates a
// single workspace's failure without blanking the rest of the shell.
createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <AppProviders>
      <ErrorBoundary boundaryLabel="the application">
        <RouterProvider router={router} />
      </ErrorBoundary>
    </AppProviders>
  </StrictMode>,
)
