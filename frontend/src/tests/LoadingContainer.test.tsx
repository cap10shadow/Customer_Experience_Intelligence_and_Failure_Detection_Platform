import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'

import { LoadingContainer, Skeleton } from '@/shared/components/feedback'

describe('LoadingContainer', () => {
  it('announces a busy region and hides children while loading', () => {
    render(
      <LoadingContainer isLoading label="Loading operational brief">
        <p>Resolved content</p>
      </LoadingContainer>,
    )

    const region = screen.getByText('Loading operational brief').closest('[aria-busy]')
    expect(region).toHaveAttribute('aria-busy', 'true')
    expect(region).toHaveAttribute('aria-live', 'polite')
    expect(screen.queryByText('Resolved content')).not.toBeInTheDocument()
  })

  it('renders resolved children and clears aria-busy once loading finishes', () => {
    render(
      <LoadingContainer isLoading={false} label="Loading operational brief">
        <p>Resolved content</p>
      </LoadingContainer>,
    )

    expect(screen.getByText('Resolved content')).toBeInTheDocument()
    expect(screen.getByText('Resolved content').closest('[aria-busy]')).toHaveAttribute('aria-busy', 'false')
  })

  it('doubles as a Suspense fallback with no children', () => {
    render(<LoadingContainer isLoading label="Loading workspace" />)
    expect(screen.getByText('Loading workspace')).toBeInTheDocument()
  })
})

describe('Skeleton', () => {
  it('renders as a decorative, non-content placeholder', () => {
    const { container } = render(<Skeleton />)
    const skeleton = container.firstElementChild
    expect(skeleton).not.toBeNull()
    expect(skeleton).not.toHaveTextContent(/.+/)
  })
})
