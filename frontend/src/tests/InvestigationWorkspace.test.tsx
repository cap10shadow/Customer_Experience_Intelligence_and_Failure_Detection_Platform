import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'

import { InvestigationsWorkspace } from '@/workspaces/investigations'

function renderWorkspace() {
  return render(
    <MemoryRouter>
      <InvestigationsWorkspace />
    </MemoryRouter>,
  )
}

describe('InvestigationsWorkspace composition', () => {
  it('renders one workspace heading and the five narrative sections in fixed order', () => {
    renderWorkspace()

    expect(screen.getByRole('heading', { level: 1, name: 'Investigations' })).toBeInTheDocument()

    const sectionHeadings = screen.getAllByRole('heading', { level: 2 }).map((heading) => heading.textContent)
    expect(sectionHeadings).toEqual([
      'Observation',
      'Evidence',
      'Root Cause Analysis',
      'Business Impact',
      'Recommended Next Step',
    ])
  })

  it('presents Evidence before Root Cause Analysis in reading order (evidence before conclusions)', () => {
    renderWorkspace()

    const headings = screen.getAllByRole('heading', { level: 2 })
    const evidenceIndex = headings.findIndex((h) => h.textContent === 'Evidence')
    const rootCauseIndex = headings.findIndex((h) => h.textContent === 'Root Cause Analysis')
    expect(evidenceIndex).toBeGreaterThanOrEqual(0)
    expect(evidenceIndex).toBeLessThan(rootCauseIndex)
  })

  it('renders the persistent Investigation Navigator with a link to every section', () => {
    renderWorkspace()

    const nav = screen.getByRole('navigation', { name: 'Investigation sections' })
    ;['Observation', 'Evidence', 'Root Cause Analysis', 'Business Impact', 'Recommended Next Step'].forEach((label) => {
      expect(screen.getByRole('link', { name: label })).toBeInTheDocument()
    })
    expect(nav).toBeInTheDocument()
  })

  it('marks the active section via aria-current when a navigator link is used', async () => {
    const user = userEvent.setup()
    renderWorkspace()

    const observationLink = screen.getByRole('link', { name: 'Observation' })
    expect(observationLink).toHaveAttribute('aria-current', 'true')

    const evidenceLink = screen.getByRole('link', { name: 'Evidence' })
    await user.click(evidenceLink)

    expect(evidenceLink).toHaveAttribute('aria-current', 'true')
    expect(observationLink).not.toHaveAttribute('aria-current')
  })

  it('shows all five canonical Business Impact dimensions, never a subset', () => {
    renderWorkspace()

    ;['Financial', 'Customer', 'Operational', 'SLA', 'Reputation'].forEach((dimension) => {
      expect(screen.getByText(dimension)).toBeInTheDocument()
    })
  })

  it('presents stage-specific confidence values that each state what they measure', () => {
    renderWorkspace()

    expect(screen.getByText(/root cause rule certainty/)).toBeInTheDocument()
    expect(screen.getByText(/business impact data completeness/)).toBeInTheDocument()
  })

  it('transitions into Recommendations with the recommendation id carried as a deep-link parameter', () => {
    renderWorkspace()

    const link = screen.getByRole('link', { name: /Open in Recommendations/ })
    expect(link).toHaveAttribute('href', '/recommendations?recommendationId=illustrative-recommendation-id')
  })

  it('never implements approval, rejection, or execution controls', () => {
    renderWorkspace()

    expect(screen.queryByRole('button', { name: /approve/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /reject/i })).not.toBeInTheDocument()
  })
})

describe('Evidence progressive disclosure', () => {
  it('collapses evidence beyond the default count and expands on request', async () => {
    const user = userEvent.setup()
    renderWorkspace()

    const expandButton = screen.getByRole('button', { name: /Show \d+ more piece/ })
    expect(expandButton).toBeInTheDocument()

    await user.click(expandButton)

    expect(screen.getByRole('button', { name: 'Show fewer' })).toBeInTheDocument()
  })

  it('selects a piece of evidence via its card, toggling aria-pressed', async () => {
    const user = userEvent.setup()
    renderWorkspace()

    const evidenceCard = screen.getByRole('button', { name: /failed payments at checkout/ })
    expect(evidenceCard).toHaveAttribute('aria-pressed', 'false')

    await user.click(evidenceCard)
    expect(evidenceCard).toHaveAttribute('aria-pressed', 'true')
  })
})
