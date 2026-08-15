import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { RouterProvider } from 'react-router-dom'

import { AppProviders } from '@/app/providers/AppProviders'
import { router } from '@/app/routing/AppRouter'

function jsonResponse(body: unknown, status = 200) {
  return { status, ok: status >= 200 && status < 300, text: async () => JSON.stringify(body) } as Response
}

describe('AppRouter (real lazy-loaded route tree)', () => {
  beforeEach(() => {
    // Phase 13 Batch 2 (AD-6): AppRouter now renders every workspace
    // route behind RequireAuth, which bootstraps a session via GET
    // /auth/me before anything else mounts. Stubbing it to resolve
    // (rather than reject, as an unmocked fetch would in jsdom) is what
    // lets this test reach the Dashboard at all -- matching the same
    // `vi.stubGlobal('fetch', ...)` convention every other integration
    // test in this file already uses (e.g. Dashboard.test.tsx). The
    // Dashboard's own data fetch (a second, distinct call) gets an
    // empty-but-valid 200 rather than the auth-shaped body, so it
    // resolves cleanly instead of entering DashboardSectionErrorGate's
    // error-recovery path -- this test asserts routing/code-splitting,
    // not Dashboard data rendering, so real data shape doesn't matter.
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation((url: string) => {
        if (String(url).includes('/auth/me')) {
          return Promise.resolve(jsonResponse({ userId: 'test-user', email: 'test@example.com', roles: [] }))
        }
        return Promise.resolve(
          jsonResponse({
            operationalBrief: { level: 'stable', summary: '', healthIndicators: [], criticalSituations: [], keyChanges: [], focusAreas: [] },
            decisionSummary: [],
            investigationEntryPoints: [],
            supportingEvidence: {},
            warnings: [],
          }),
        )
      }),
    )
  })

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
