import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import { DashboardContextProvider, useDashboardContext } from '@/workspaces/dashboard/context'

function ContextProbe({ id }: { id: string }) {
  const { timeRange, region, businessUnit, productScope, userScope, setTimeRange } = useDashboardContext()
  return (
    <div>
      <span data-testid={`${id}-timeRange`}>{timeRange}</span>
      <span data-testid={`${id}-region`}>{region ?? 'all'}</span>
      <span data-testid={`${id}-businessUnit`}>{businessUnit ?? 'all'}</span>
      <span data-testid={`${id}-productScope`}>{productScope ?? 'all'}</span>
      <span data-testid={`${id}-userScope`}>{userScope ?? 'all'}</span>
      <button type="button" onClick={() => setTimeRange('7d')}>
        Set 7d ({id})
      </button>
    </div>
  )
}

describe('Global Dashboard Context', () => {
  it('throws when consumed outside a DashboardContextProvider', () => {
    // React logs the thrown error to console.error during render; suppress it for a clean test run.
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
    expect(() => render(<ContextProbe id="orphan" />)).toThrow(/DashboardContextProvider/)
    consoleError.mockRestore()
  })

  it('provides unscoped defaults -- "all" scope, current time range -- until a future filter sets otherwise', () => {
    render(
      <DashboardContextProvider>
        <ContextProbe id="a" />
      </DashboardContextProvider>,
    )

    expect(screen.getByTestId('a-timeRange')).toHaveTextContent('current')
    expect(screen.getByTestId('a-region')).toHaveTextContent('all')
    expect(screen.getByTestId('a-businessUnit')).toHaveTextContent('all')
    expect(screen.getByTestId('a-productScope')).toHaveTextContent('all')
    expect(screen.getByTestId('a-userScope')).toHaveTextContent('all')
  })

  it('keeps every consumer in agreement -- changing scope in one place updates all sections consistently', async () => {
    const user = userEvent.setup()
    render(
      <DashboardContextProvider>
        <ContextProbe id="brief" />
        <ContextProbe id="decisions" />
      </DashboardContextProvider>,
    )

    expect(screen.getByTestId('brief-timeRange')).toHaveTextContent('current')
    expect(screen.getByTestId('decisions-timeRange')).toHaveTextContent('current')

    await user.click(screen.getByRole('button', { name: 'Set 7d (brief)' }))

    expect(screen.getByTestId('brief-timeRange')).toHaveTextContent('7d')
    expect(screen.getByTestId('decisions-timeRange')).toHaveTextContent('7d')
  })
})
