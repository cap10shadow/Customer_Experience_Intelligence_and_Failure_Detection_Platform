import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'

import {
  ConfidencePresentation,
  InvestigationEmptyState,
  InvestigationLoadingState,
  InvestigationSection,
} from '@/workspaces/investigations/components/foundation'

describe('InvestigationSection', () => {
  it('renders a level-2 heading, a framing description, and an anchor target', () => {
    const { container } = render(
      <InvestigationSection id="observation" title="Observation" description="What happened?">
        <p>Content</p>
      </InvestigationSection>,
    )

    expect(screen.getByRole('heading', { level: 2, name: 'Observation' })).toBeInTheDocument()
    expect(screen.getByText('What happened?')).toBeInTheDocument()
    expect(container.querySelector('#observation')).not.toBeNull()
  })
})

describe('InvestigationEmptyState', () => {
  it('explains absence instead of stating "No Data"', () => {
    render(
      <InvestigationEmptyState
        title="No evidence gathered yet"
        description="This investigation hasn't collected supporting evidence for this stage yet. Evidence appears here as soon as an upstream intelligence stage contributes it."
      />,
    )

    expect(screen.getByText('No evidence gathered yet')).toBeInTheDocument()
    expect(screen.queryByText(/no data/i)).not.toBeInTheDocument()
  })
})

describe('InvestigationLoadingState', () => {
  it('announces a busy region with skeleton shapes', () => {
    const { container } = render(<InvestigationLoadingState label="Loading evidence" />)

    expect(container.querySelector('[aria-busy="true"]')).not.toBeNull()
    expect(screen.getByText('Loading evidence')).toBeInTheDocument()
  })
})

describe('ConfidencePresentation (ARB-008: stage-specific, never a shared score)', () => {
  it('always renders the level together with what it measures, never a bare label', () => {
    render(<ConfidencePresentation level="moderate" measures="root cause rule certainty" />)

    expect(screen.getByText(/Moderate confidence/)).toBeInTheDocument()
    expect(screen.getByText(/root cause rule certainty/)).toBeInTheDocument()
  })

  it('renders distinct text for different stages even at the same level, so two confidences are never mistaken for one scale', () => {
    const { rerender } = render(<ConfidencePresentation level="high" measures="root cause rule certainty" />)
    expect(screen.getByText(/root cause rule certainty/)).toBeInTheDocument()

    rerender(<ConfidencePresentation level="high" measures="business impact data completeness" />)
    expect(screen.getByText(/business impact data completeness/)).toBeInTheDocument()
    expect(screen.queryByText(/root cause rule certainty/)).not.toBeInTheDocument()
  })
})
