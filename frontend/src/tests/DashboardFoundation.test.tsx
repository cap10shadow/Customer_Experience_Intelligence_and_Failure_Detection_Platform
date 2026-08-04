import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'

import {
  DashboardDrillDownLink,
  DashboardEmptyState,
  DashboardLoadingState,
  DashboardSection,
  DashboardSubsectionHeading,
} from '@/workspaces/dashboard/components/foundation'

describe('DashboardSection (Universal Information Hierarchy)', () => {
  it('always renders a Headline and a Primary Insight', () => {
    render(
      <DashboardSection title="Decision summary" insight="The judgment calls most worth your attention.">
        <p>Supporting context</p>
      </DashboardSection>,
    )

    expect(screen.getByRole('heading', { name: 'Decision summary' })).toBeInTheDocument()
    expect(screen.getByText('The judgment calls most worth your attention.')).toBeInTheDocument()
    expect(screen.getByText('Supporting context')).toBeInTheDocument()
  })

  it('renders Why It Matters only when provided', () => {
    const { rerender } = render(
      <DashboardSection title="Supporting evidence" insight="Analytical context.">
        <p>Content</p>
      </DashboardSection>,
    )
    expect(screen.queryByText(/does not replace them/)).not.toBeInTheDocument()

    rerender(
      <DashboardSection
        title="Supporting evidence"
        insight="Analytical context."
        whyItMatters="Evidence increases confidence in the conclusions above; it does not replace them."
      >
        <p>Content</p>
      </DashboardSection>,
    )
    expect(screen.getByText(/does not replace them/)).toBeInTheDocument()
  })

  it('defaults to a level-2 heading and supports level-3 for nested subsections', () => {
    const { rerender } = render(
      <DashboardSection title="Operational brief" insight="Situational awareness.">
        <p>Content</p>
      </DashboardSection>,
    )
    expect(screen.getByRole('heading', { level: 2, name: 'Operational brief' })).toBeInTheDocument()

    rerender(
      <DashboardSection title="Critical situations" insight="Only significant situations." headingLevel={3}>
        <p>Content</p>
      </DashboardSection>,
    )
    expect(screen.getByRole('heading', { level: 3, name: 'Critical situations' })).toBeInTheDocument()
  })
})

describe('DashboardEmptyState (Stability Philosophy)', () => {
  it('renders confident copy, never generic "No Data"', () => {
    render(<DashboardEmptyState title="No critical situations" description="Operations remain within expected thresholds." />)

    expect(screen.getByText('No critical situations')).toBeInTheDocument()
    expect(screen.queryByText(/no data/i)).not.toBeInTheDocument()
  })
})

describe('DashboardLoadingState (skeleton-first loading)', () => {
  it('announces a busy region with a screen-reader label and renders skeleton shapes, not a spinner', () => {
    const { container } = render(<DashboardLoadingState label="Loading decision opportunity" />)

    const region = container.querySelector('[aria-busy="true"]')
    expect(region).not.toBeNull()
    expect(region).toHaveAttribute('aria-live', 'polite')
    expect(screen.getByText('Loading decision opportunity')).toBeInTheDocument()
    expect(container.querySelectorAll('[aria-hidden="true"]').length).toBeGreaterThan(0)
  })
})

describe('DashboardSubsectionHeading (landmark-free subsection structure)', () => {
  it('renders a real level-3 heading with no surrounding landmark region', () => {
    const { container } = render(<DashboardSubsectionHeading title="Critical situations" description="Only significant situations." />)

    expect(screen.getByRole('heading', { level: 3, name: 'Critical situations' })).toBeInTheDocument()
    expect(screen.getByText('Only significant situations.')).toBeInTheDocument()
    expect(container.querySelector('section')).toBeNull()
    expect(screen.queryByRole('region')).not.toBeInTheDocument()
  })

  it('omits the description paragraph when none is given', () => {
    render(<DashboardSubsectionHeading title="Operational health snapshot" />)
    expect(screen.getByRole('heading', { level: 3, name: 'Operational health snapshot' })).toBeInTheDocument()
  })
})

describe('DashboardDrillDownLink (shared card affordance)', () => {
  it('renders a real, labelled link to the given path', () => {
    render(
      <MemoryRouter>
        <DashboardDrillDownLink to="/investigations" label="Investigate this story" />
      </MemoryRouter>,
    )

    expect(screen.getByRole('link', { name: 'Investigate this story' })).toHaveAttribute('href', '/investigations')
  })
})
