import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'

import {
  FutureCapabilityPlaceholder,
  RecommendationEmptyState,
  RecommendationLoadingState,
  RecommendationSection,
} from '@/workspaces/recommendations/components/foundation'
import { LifecycleSummary } from '@/workspaces/recommendations/components/RecommendationLifecycle'
import type { DecisionRecord } from '@/workspaces/recommendations/types'

describe('RecommendationSection', () => {
  it('renders a level-2 heading, a framing description, and an anchor target', () => {
    const { container } = render(
      <RecommendationSection id="overview" title="Recommendation Overview" description="What is being recommended?">
        <p>Content</p>
      </RecommendationSection>,
    )

    expect(screen.getByRole('heading', { level: 2, name: 'Recommendation Overview' })).toBeInTheDocument()
    expect(screen.getByText('What is being recommended?')).toBeInTheDocument()
    expect(container.querySelector('#overview')).not.toBeNull()
  })
})

describe('RecommendationEmptyState', () => {
  it('explains and reassures rather than stating "No Data"', () => {
    render(<RecommendationEmptyState title="Lifecycle begins once a decision is made" description="Explained here." />)
    expect(screen.getByText('Lifecycle begins once a decision is made')).toBeInTheDocument()
    expect(screen.queryByText(/no data/i)).not.toBeInTheDocument()
  })
})

describe('RecommendationLoadingState', () => {
  it('announces a busy region with skeleton shapes', () => {
    const { container } = render(<RecommendationLoadingState label="Loading decision" />)
    expect(container.querySelector('[aria-busy="true"]')).not.toBeNull()
    expect(screen.getByText('Loading decision')).toBeInTheDocument()
  })
})

describe('FutureCapabilityPlaceholder (UX-003)', () => {
  it('never renders "No Data" or "Empty" copy', () => {
    render(
      <FutureCapabilityPlaceholder
        title="Alternative option comparison is a future capability"
        description="Coming in a future step."
      />,
    )
    expect(screen.getByText('Alternative option comparison is a future capability')).toBeInTheDocument()
    expect(screen.queryByText(/no data/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/^empty$/i)).not.toBeInTheDocument()
  })
})

describe('LifecycleSummary (Decision Before Lifecycle)', () => {
  const pending: DecisionRecord = { status: 'pending-review', note: 'Awaiting review.' }
  const approved: DecisionRecord = { status: 'approved', note: 'Approved.' }
  const rejected: DecisionRecord = { status: 'rejected', note: 'Rejected.' }
  const deferred: DecisionRecord = { status: 'deferred', note: 'Deferred.' }

  it('shows no stage progression while Pending Review', () => {
    render(<LifecycleSummary decision={pending} />)
    expect(screen.getByText('Lifecycle begins once a decision is made')).toBeInTheDocument()
    expect(screen.queryByRole('list')).not.toBeInTheDocument()
  })

  it('shows the full stage progression once Approved', () => {
    render(<LifecycleSummary decision={approved} currentStage="awaiting-implementation" />)
    expect(screen.getByText('Awaiting Implementation')).toBeInTheDocument()
    expect(screen.getByText('Outcome Evaluation')).toBeInTheDocument()
    expect(screen.getByText('Completed')).toBeInTheDocument()
  })

  it('represents Rejected as its own terminal state, not a broken Approved path', () => {
    render(<LifecycleSummary decision={rejected} />)
    expect(screen.getByText('This recommendation was rejected')).toBeInTheDocument()
    expect(screen.queryByText('Awaiting Implementation')).not.toBeInTheDocument()
  })

  it('represents Deferred as its own state, not a broken Approved path', () => {
    render(<LifecycleSummary decision={deferred} />)
    expect(screen.getByText('This recommendation was deferred')).toBeInTheDocument()
    expect(screen.queryByText('Awaiting Implementation')).not.toBeInTheDocument()
  })
})
