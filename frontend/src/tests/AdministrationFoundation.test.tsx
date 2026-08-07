import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'

import {
  AdministrationEmptyState,
  AdministrationLoadingState,
  AdministrationSection,
  AdministrationSubsectionHeading,
} from '@/workspaces/administration/components/foundation'

describe('AdministrationSection', () => {
  it('renders a level-2 heading, a framing description, and an anchor target', () => {
    const { container } = render(
      <AdministrationSection
        id="platform-overview"
        title="Platform Overview"
        description="The current operational state of the platform."
        register="state"
      >
        <p>Content</p>
      </AdministrationSection>,
    )

    expect(screen.getByRole('heading', { level: 2, name: 'Platform Overview' })).toBeInTheDocument()
    expect(screen.getByText('The current operational state of the platform.')).toBeInTheDocument()
    expect(container.querySelector('#platform-overview')).not.toBeNull()
  })

  it('carries its register as a data attribute for presentation rhythm only, never a new landmark or grouping', () => {
    const { container } = render(
      <AdministrationSection id="intelligence-configuration" title="Intelligence Configuration" description="How is platform intelligence configured?" register="configuration">
        <p>Content</p>
      </AdministrationSection>,
    )

    expect(container.querySelector('[data-register="configuration"]')).not.toBeNull()
    // Exactly one section landmark -- the register never introduces a second one.
    expect(container.querySelectorAll('section')).toHaveLength(1)
  })
})

describe('AdministrationSubsectionHeading', () => {
  it('renders a real h3 without introducing a new section landmark', () => {
    const { container } = render(<AdministrationSubsectionHeading title="Connected Services" description="Infrastructure this instance depends on." />)
    expect(screen.getByRole('heading', { level: 3, name: 'Connected Services' })).toBeInTheDocument()
    expect(container.querySelector('section')).toBeNull()
  })
})

describe('AdministrationEmptyState', () => {
  it('explains and reassures rather than stating "No Data" or "Empty"', () => {
    render(
      <AdministrationEmptyState
        title="No administrative actions have been recorded yet"
        description="Every configuration change will be permanently recorded here as it happens."
      />,
    )
    expect(screen.getByText('No administrative actions have been recorded yet')).toBeInTheDocument()
    expect(screen.queryByText(/no data/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/^empty$/i)).not.toBeInTheDocument()
  })
})

describe('AdministrationLoadingState', () => {
  it('announces a busy region with skeleton shapes', () => {
    const { container } = render(<AdministrationLoadingState label="Loading platform fact" />)
    expect(container.querySelector('[aria-busy="true"]')).not.toBeNull()
    expect(screen.getByText('Loading platform fact')).toBeInTheDocument()
  })
})
