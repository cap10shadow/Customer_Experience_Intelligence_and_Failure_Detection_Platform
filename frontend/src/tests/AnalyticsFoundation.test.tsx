import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'

import {
  AnalyticsEmptyState,
  AnalyticsLoadingState,
  AnalyticsSection,
} from '@/workspaces/analytics/components/foundation'

describe('AnalyticsSection', () => {
  it('renders a level-2 heading, a framing description, and an anchor target', () => {
    const { container } = render(
      <AnalyticsSection id="executive-overview" title="Executive Overview" description="What changed?">
        <p>Content</p>
      </AnalyticsSection>,
    )

    expect(screen.getByRole('heading', { level: 2, name: 'Executive Overview' })).toBeInTheDocument()
    expect(screen.getByText('What changed?')).toBeInTheDocument()
    expect(container.querySelector('#executive-overview')).not.toBeNull()
  })
})

describe('AnalyticsEmptyState', () => {
  it('explains rather than stating "No Analytics"', () => {
    render(
      <AnalyticsEmptyState
        title="Organizational learning grows over time"
        description="Insights become available as operational history accumulates."
      />,
    )
    expect(screen.getByText('Organizational learning grows over time')).toBeInTheDocument()
    expect(screen.queryByText(/no analytics/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/no data/i)).not.toBeInTheDocument()
  })
})

describe('AnalyticsLoadingState', () => {
  it('announces a busy region with skeleton shapes', () => {
    const { container } = render(<AnalyticsLoadingState label="Loading trend" />)
    expect(container.querySelector('[aria-busy="true"]')).not.toBeNull()
    expect(screen.getByText('Loading trend')).toBeInTheDocument()
  })
})
