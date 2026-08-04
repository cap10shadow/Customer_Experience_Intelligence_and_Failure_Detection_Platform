import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import { ErrorBoundary } from '@/shared/components/feedback'

function Explode(): never {
  throw new Error('workspace failed to load')
}

describe('ErrorBoundary', () => {
  it('renders a labelled fallback instead of crashing when a child throws', () => {
    // React logs the caught error to console.error; suppress it for a clean test run.
    vi.spyOn(console, 'error').mockImplementation(() => {})

    render(
      <ErrorBoundary boundaryLabel="the Analytics workspace">
        <Explode />
      </ErrorBoundary>,
    )

    const alert = screen.getByRole('alert')
    expect(alert).toHaveTextContent('Something went wrong loading the Analytics workspace')
    expect(alert).toHaveTextContent('workspace failed to load')

    vi.restoreAllMocks()
  })

  it('renders children normally when nothing throws', () => {
    render(
      <ErrorBoundary boundaryLabel="the Analytics workspace">
        <p>All good</p>
      </ErrorBoundary>,
    )
    expect(screen.getByText('All good')).toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('exposes a retry button that resets the boundary state', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {})
    const user = userEvent.setup()

    render(
      <ErrorBoundary boundaryLabel="the Analytics workspace">
        <Explode />
      </ErrorBoundary>,
    )

    const retryButton = screen.getByRole('button', { name: 'Try again' })
    expect(retryButton).toBeInTheDocument()
    await user.click(retryButton)

    vi.restoreAllMocks()
  })
})
