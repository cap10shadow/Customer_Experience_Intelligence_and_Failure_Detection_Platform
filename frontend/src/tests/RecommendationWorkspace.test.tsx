import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'

import { RecommendationsWorkspace } from '@/workspaces/recommendations'

function renderWorkspace() {
  return render(
    <MemoryRouter>
      <RecommendationsWorkspace />
    </MemoryRouter>,
  )
}

describe('RecommendationsWorkspace composition', () => {
  it('renders one workspace heading and the seven sections in fixed order', () => {
    renderWorkspace()

    expect(screen.getByRole('heading', { level: 1, name: 'Recommendations' })).toBeInTheDocument()

    const sectionHeadings = screen.getAllByRole('heading', { level: 2 }).map((heading) => heading.textContent)
    expect(sectionHeadings).toEqual([
      'Recommendation Overview',
      'Recommendation Rationale',
      'Alternative Options',
      'Expected Outcome',
      'Risk Assessment',
      'Decision',
      'Recommendation Lifecycle',
    ])
  })

  it('renders the persistent Recommendation Navigator with a link to every section (UX-004: reuses the Investigation navigation model)', () => {
    renderWorkspace()

    expect(screen.getByRole('navigation', { name: 'Recommendation sections' })).toBeInTheDocument()
    ;[
      'Recommendation Overview',
      'Recommendation Rationale',
      'Alternative Options',
      'Expected Outcome',
      'Risk Assessment',
      'Decision',
      'Recommendation Lifecycle',
    ].forEach((label) => {
      expect(screen.getByRole('link', { name: label })).toBeInTheDocument()
    })
  })

  it('marks the active section via aria-current when a navigator link is used', async () => {
    const user = userEvent.setup()
    renderWorkspace()

    const overviewLink = screen.getByRole('link', { name: 'Recommendation Overview' })
    expect(overviewLink).toHaveAttribute('aria-current', 'true')

    const rationaleLink = screen.getByRole('link', { name: 'Recommendation Rationale' })
    await user.click(rationaleLink)

    expect(rationaleLink).toHaveAttribute('aria-current', 'true')
    expect(overviewLink).not.toHaveAttribute('aria-current')
  })

  it('shows a persistent, calm Decision reference (UX-001) that honestly states no decision has been recorded yet -- never a fabricated "Pending Review" status or a floating action toolbar', () => {
    renderWorkspace()

    expect(screen.getByText('Current status')).toBeInTheDocument()
    const nav = screen.getByRole('navigation', { name: 'Recommendation sections' })
    expect(nav).toHaveTextContent('Decision capability not yet available')
    expect(nav).not.toHaveTextContent('Pending Review')
    expect(screen.queryByRole('toolbar')).not.toBeInTheDocument()
  })

  it('renders the real Decision form (Step 7.X G-01) with no route param, since there is no recommendationId to submit against', () => {
    renderWorkspace()

    // No :recommendationId route param -- onSubmitDecision is intentionally undefined, so no form renders.
    expect(screen.queryByRole('button', { name: /save decision/i })).not.toBeInTheDocument()
  })

  it('presents Alternative Options as a future capability, never "No Data" or "Empty" (UX-003)', () => {
    renderWorkspace()

    expect(screen.getByText('Alternative option comparison is a future capability')).toBeInTheDocument()
    expect(screen.queryByText(/no data/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/^empty$/i)).not.toBeInTheDocument()
  })

  it('enforces Decision Before Lifecycle: with no decision yet, Lifecycle presents an honest future-capability placeholder, never stage progression (Step 7.X A-07)', () => {
    renderWorkspace()

    expect(screen.getByText('Recommendation lifecycle tracking is a future capability')).toBeInTheDocument()
    expect(screen.queryByText('Awaiting Implementation')).not.toBeInTheDocument()
    expect(screen.queryByText('Completed')).not.toBeInTheDocument()
  })

  it('references the originating Incident from Rationale, never introducing a separate investigation identifier in the URL', () => {
    renderWorkspace()

    // No :recommendationId route param here, so no real incidentId has been
    // fetched yet -- the link degrades to the bare Investigations path
    // rather than fabricating an incidentId.
    const link = screen.getByRole('link', { name: /Review the full investigation/ })
    expect(link).toHaveAttribute('href', '/investigations')
  })

  it('never implements approval, rejection, or workflow controls anywhere in the workspace', () => {
    renderWorkspace()

    expect(screen.queryByRole('button', { name: /approve/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /reject/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /defer/i })).not.toBeInTheDocument()
  })
})

describe('Risk Assessment (UX-002 regression protection)', () => {
  it('never renders a critical- or warning-toned element anywhere in the workspace', () => {
    const { container } = renderWorkspace()

    // StatusIndicator/Badge apply their tone as a CSS-module class carrying
    // the literal tone name (e.g. "_critical_x1y2z3") -- this guards UX-002
    // ("never warning styling, stronger colors, or alarm visuals") against a
    // future edit accidentally introducing one, in Risk Assessment or
    // anywhere else in this calm-software workspace.
    expect(container.querySelectorAll('[class*="critical"]')).toHaveLength(0)
    expect(container.querySelectorAll('[class*="warning"]')).toHaveLength(0)
  })

  it('presents Risk Assessment as a future capability, never "No Data" or "Empty" (UX-003) -- recommendation_service has no risk-assessment capability today', () => {
    renderWorkspace()

    const riskHeading = screen.getByRole('heading', { level: 2, name: 'Risk Assessment' })
    const riskSection = riskHeading.closest('section')
    expect(riskSection).not.toBeNull()

    expect(screen.getByText('Risk assessment is a future capability')).toBeInTheDocument()
    expect(riskSection?.querySelectorAll('[class*="critical"]')).toHaveLength(0)
    expect(riskSection?.querySelectorAll('[class*="warning"]')).toHaveLength(0)
    expect(riskSection?.querySelector('[role="alert"]')).toBeNull()
  })
})

describe('Expected Outcome (no fabricated outcome data)', () => {
  it('presents Expected Outcome as a future capability, never "No Data" or "Empty" (UX-003) -- recommendation_service has no outcome-tracking capability today', () => {
    renderWorkspace()

    expect(screen.getByText('Expected outcome tracking is a future capability')).toBeInTheDocument()
    expect(screen.queryByText('Operational improvement')).not.toBeInTheDocument()
  })
})
