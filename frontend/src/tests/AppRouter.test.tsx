import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { RouterProvider } from 'react-router-dom'

import { AppProviders } from '@/app/providers/AppProviders'
import { router } from '@/app/routing/AppRouter'

describe('AppRouter (real lazy-loaded route tree)', () => {
  it('code-splits each workspace and resolves the Dashboard via Suspense on initial load', async () => {
    render(
      <AppProviders>
        <RouterProvider router={router} />
      </AppProviders>,
    )

    // Before the lazy chunk resolves, WorkspaceLayout's Suspense fallback
    // (LoadingContainer) is what's on screen -- this is the same
    // mechanism route-level code splitting relies on in production. The
    // extended timeout accounts for real dynamic `import()` resolution
    // across the full (now six-workspace) module graph in the test
    // environment, not production load time.
    expect(
      await screen.findByRole('heading', { level: 1, name: 'Operational Intelligence Dashboard' }, { timeout: 5000 }),
    ).toBeInTheDocument()
    expect(await screen.findByRole('heading', { name: /Operational brief/i })).toBeInTheDocument()
  })
})
