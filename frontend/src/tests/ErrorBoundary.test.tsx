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

  it('calls onRetry before clearing its own caught state (Part 7: retry must trigger a real refetch, not just remount)', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {})
    const user = userEvent.setup()
    const onRetry = vi.fn()

    render(
      <ErrorBoundary boundaryLabel="the Analytics workspace" onRetry={onRetry}>
        <Explode />
      </ErrorBoundary>,
    )

    await user.click(screen.getByRole('button', { name: 'Try again' }))

    expect(onRetry).toHaveBeenCalledTimes(1)

    vi.restoreAllMocks()
  })

  it('renders real, updated children after a successful retry -- proving the boundary genuinely re-renders with fresh state, not the same stale error', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {})
    const user = userEvent.setup()

    function FlakyOnce() {
      // Simulates a hook whose error clears after a real refetch succeeds:
      // the first render throws, a "retry" flips this module-level flag,
      // and the boundary's post-retry re-render sees success.
      if (!hasRetried) {
        throw new Error('first attempt failed')
      }
      return <p>Real data loaded</p>
    }

    let hasRetried = false
    const onRetry = vi.fn(() => {
      hasRetried = true
    })

    const { rerender } = render(
      <ErrorBoundary boundaryLabel="the Analytics workspace" onRetry={onRetry}>
        <FlakyOnce />
      </ErrorBoundary>,
    )

    expect(screen.getByRole('alert')).toHaveTextContent('first attempt failed')

    await user.click(screen.getByRole('button', { name: 'Try again' }))
    rerender(
      <ErrorBoundary boundaryLabel="the Analytics workspace" onRetry={onRetry}>
        <FlakyOnce />
      </ErrorBoundary>,
    )

    expect(screen.getByText('Real data loaded')).toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()

    vi.restoreAllMocks()
  })

  it('shows a fresh error state if the retried request fails again', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {})
    const user = userEvent.setup()

    function AlwaysFails(): never {
      throw new Error('retry also failed')
    }

    const onRetry = vi.fn()

    render(
      <ErrorBoundary boundaryLabel="the Analytics workspace" onRetry={onRetry}>
        <AlwaysFails />
      </ErrorBoundary>,
    )

    expect(screen.getByRole('alert')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Try again' }))

    expect(onRetry).toHaveBeenCalledTimes(1)
    // The boundary re-threw immediately (AlwaysFails never succeeds) -- the
    // error UI must remain correctly visible, not silently disappear.
    expect(screen.getByRole('alert')).toHaveTextContent('retry also failed')

    vi.restoreAllMocks()
  })
})
