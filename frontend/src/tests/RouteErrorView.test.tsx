import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { RouterProvider, createMemoryRouter } from 'react-router-dom'

import { PRIMARY_NAVIGATION } from '@/app/configuration/navigation.config'
import { AppProviders } from '@/app/providers/AppProviders'
import { router } from '@/app/routing/AppRouter'

function jsonResponse(body: unknown, status = 200) {
  return { status, ok: status >= 200 && status < 300, text: async () => JSON.stringify(body) } as Response
}

/**
 * Covers the two halves of the "unreachable URL" defect together,
 * because they are one behaviour from the user's side: primary
 * navigation must never offer a path the router cannot resolve, and any
 * path the router still cannot resolve must land on a real product
 * surface rather than react-router's raw developer error screen.
 */
describe('unreachable routes', () => {
  beforeEach(() => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation((url: string) => {
        if (String(url).includes('/auth/me')) {
          return Promise.resolve(jsonResponse({ userId: 'test-user', email: 'test@example.com', roles: [] }))
        }
        return Promise.resolve(jsonResponse({}))
      }),
    )
  })

  it('never lists a primary navigation entry the router cannot resolve', () => {
    const navigationIds = PRIMARY_NAVIGATION.map((item) => item.id)

    // `/investigations` and `/recommendations` exist only as
    // parameterized detail routes, reached by drill-down from Dashboard
    // -- there is no list view behind the bare path.
    expect(navigationIds).not.toContain('investigations')
    expect(navigationIds).not.toContain('recommendations')
    expect(navigationIds).toEqual(['ingestion', 'dashboard', 'analytics', 'administration'])
  })

  it('renders the product not-found surface for an unmatched URL, not a raw router error', async () => {
    const memoryRouter = createMemoryRouter(router.routes, { initialEntries: ['/investigations'] })

    render(
      <AppProviders>
        <RouterProvider router={memoryRouter} />
      </AppProviders>,
    )

    expect(await screen.findByText('This page does not exist', undefined, { timeout: 5000 })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Back to Dashboard' })).toHaveAttribute('href', '/')
  })
})
