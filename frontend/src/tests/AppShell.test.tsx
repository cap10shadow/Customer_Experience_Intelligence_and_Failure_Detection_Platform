import { describe, expect, it } from 'vitest'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'

import { AppShell } from '@/app/layouts/AppShell'
import { AppProviders } from '@/app/providers/AppProviders'
import { ROUTE_PATHS } from '@/app/routing/routePaths'
import { PRIMARY_NAVIGATION } from '@/app/configuration/navigation.config'
import { DashboardWorkspace } from '@/workspaces/dashboard'
import { AnalyticsWorkspace } from '@/workspaces/analytics'

function renderApp(initialPath: string) {
  const router = createMemoryRouter(
    [
      {
        path: '/',
        element: <AppShell />,
        children: [
          { index: true, element: <DashboardWorkspace /> },
          { path: ROUTE_PATHS.analytics, element: <AnalyticsWorkspace /> },
        ],
      },
    ],
    { initialEntries: [initialPath] },
  )
  return render(
    <AppProviders>
      <RouterProvider router={router} />
    </AppProviders>,
  )
}

describe('AppShell', () => {
  it('renders the persistent primary landmarks', async () => {
    renderApp('/')
    expect(screen.getByRole('navigation', { name: 'Primary' })).toBeInTheDocument()
    expect(await screen.findByRole('main')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Skip to main content' })).toBeInTheDocument()
  })

  it('renders every workspace as a primary navigation entry', async () => {
    renderApp('/')
    const nav = screen.getByRole('navigation', { name: 'Primary' })
    for (const item of PRIMARY_NAVIGATION) {
      expect(await within(nav).findByRole('link', { name: new RegExp(item.label) })).toBeInTheDocument()
    }
  })

  it('marks the active workspace link with aria-current', async () => {
    renderApp('/')
    const dashboardLink = await screen.findByRole('link', { name: /Dashboard/ })
    expect(dashboardLink).toHaveAttribute('aria-current', 'page')
  })

  it('navigates to another workspace via the sidebar', async () => {
    const user = userEvent.setup()
    renderApp('/')
    await screen.findByRole('heading', { name: /Operational brief/i })

    const analyticsLink = screen.getByRole('link', { name: /Analytics/ })
    await user.click(analyticsLink)

    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 1, name: 'Analytics' })).toBeInTheDocument()
    })
  })
})
