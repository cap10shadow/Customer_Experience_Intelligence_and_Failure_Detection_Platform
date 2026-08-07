import { describe, expect, it } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'

import { AnalyticsWorkspace } from '@/workspaces/analytics'

function mountWorkspace() {
  return render(
    <MemoryRouter>
      <AnalyticsWorkspace />
    </MemoryRouter>,
  )
}

/**
 * AnalyticsWorkspace owns a real (if brief) initial loading state and
 * passes it through the composed section hierarchy -- so composition
 * assertions that need loaded content wait for that transition to
 * finish, exactly as they would against a real data load.
 */
async function renderWorkspace() {
  const utils = mountWorkspace()
  await waitFor(() => {
    expect(document.querySelectorAll('[aria-busy="true"]')).toHaveLength(0)
  })
  return utils
}

describe('AnalyticsWorkspace loading (real composition hierarchy)', () => {
  it('starts every section busy and transitions to loaded content once the workspace load completes, without a static isLoading prop', async () => {
    mountWorkspace()

    // Immediately after mount: sections are busy and real content is
    // suppressed, driven by AnalyticsWorkspace's own state -- not a
    // hardcoded `isLoading` prop passed in by the test.
    expect(document.querySelectorAll('[aria-busy="true"]').length).toBeGreaterThan(0)
    expect(
      screen.queryByText('Checkout-related complaints tend to recur around provider changes'),
    ).not.toBeInTheDocument()

    await waitFor(() => {
      expect(document.querySelectorAll('[aria-busy="true"]')).toHaveLength(0)
    })

    expect(
      screen.getByText('Checkout-related complaints tend to recur around provider changes'),
    ).toBeInTheDocument()
  })
})

describe('AnalyticsWorkspace composition', () => {
  it('renders one workspace heading and the six sections in fixed order', async () => {
    await renderWorkspace()

    expect(screen.getByRole('heading', { level: 1, name: 'Analytics' })).toBeInTheDocument()

    const sectionHeadings = screen.getAllByRole('heading', { level: 2 }).map((heading) => heading.textContent)
    expect(sectionHeadings).toEqual([
      'Executive Overview',
      'Trend Analysis',
      'Pattern Discovery',
      'Recommendation Effectiveness',
      'Organizational Insights',
      'Strategic Opportunities',
    ])
  })

  it('renders the persistent Analytics Navigator with a link to every section (UX-009: reuses the Investigation/Recommendation navigator family)', async () => {
    await renderWorkspace()

    expect(screen.getByRole('navigation', { name: 'Analytics sections' })).toBeInTheDocument()
    ;[
      'Executive Overview',
      'Trend Analysis',
      'Pattern Discovery',
      'Recommendation Effectiveness',
      'Organizational Insights',
      'Strategic Opportunities',
    ].forEach((label) => {
      expect(screen.getByRole('link', { name: label })).toBeInTheDocument()
    })
  })

  it('marks the active section via aria-current when a navigator link is used', async () => {
    const user = userEvent.setup()
    await renderWorkspace()

    const overviewLink = screen.getByRole('link', { name: 'Executive Overview' })
    expect(overviewLink).toHaveAttribute('aria-current', 'true')

    const trendLink = screen.getByRole('link', { name: 'Trend Analysis' })
    await user.click(trendLink)

    expect(trendLink).toHaveAttribute('aria-current', 'true')
    expect(overviewLink).not.toHaveAttribute('aria-current')
  })

  it('shows the shared Scope Indicator once, in the navigator, and no section restates it (UX-005)', async () => {
    await renderWorkspace()

    expect(screen.getByText('Analysis period')).toBeInTheDocument()
    expect(screen.getByText('Last 30 days')).toBeInTheDocument()
    expect(screen.getByText('Filters')).toBeInTheDocument()

    // Only one Scope Indicator exists workspace-wide -- individual sections
    // never restate the period, unlike Dashboard's Step 2 sections which
    // each appended their own time-range caption.
    expect(screen.getAllByText('Last 30 days')).toHaveLength(1)
    expect(screen.queryByText(/reflecting/i)).not.toBeInTheDocument()
  })

  it('presents Recommendation Effectiveness as a future capability, reusing the same shared placeholder Recommendation Workspace uses (UX-007)', async () => {
    await renderWorkspace()

    expect(screen.getByText('Recommendation effectiveness is a future capability')).toBeInTheDocument()
    expect(screen.queryByText(/no data/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/^empty$/i)).not.toBeInTheDocument()
  })

  it('presents Pattern Discovery with narrative structure, not a bare list (UX-008)', async () => {
    await renderWorkspace()

    expect(screen.getByText('Checkout-related complaints tend to recur around provider changes')).toBeInTheDocument()
    expect(screen.getByText(/Supported by recurring correlation/)).toBeInTheDocument()
    expect(screen.queryByRole('list', { name: /patterns/i })).not.toBeInTheDocument()
  })

  it('Executive Overview stays descriptive -- no evaluative or recommending language', async () => {
    await renderWorkspace()

    const overviewHeading = screen.getByRole('heading', { level: 2, name: 'Executive Overview' })
    const overviewSection = overviewHeading.closest('section')
    expect(overviewSection).not.toBeNull()
    // Matches evaluative/prescriptive phrasing specifically -- not the bare
    // noun "recommendations" (Executive Overview legitimately reports a
    // count of recommendations generated, which is a fact, not a judgment).
    expect(overviewSection?.textContent).not.toMatch(/\bshould\b|\bwe recommend\b|\bimproved\b|\bdeclined\b|\bworsened\b/i)
  })

  it('never implements approval, assignment, or workflow controls anywhere in Strategic Opportunities', async () => {
    await renderWorkspace()

    const opportunitiesHeading = screen.getByRole('heading', { level: 2, name: 'Strategic Opportunities' })
    const opportunitiesSection = opportunitiesHeading.closest('section')
    expect(opportunitiesSection?.querySelector('[aria-pressed]')).toBeNull()
    expect(screen.queryByRole('button', { name: /approve/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /assign/i })).not.toBeInTheDocument()
  })
})

describe('Organizational Insights (UX-006: distinct rhythm, never distinct color)', () => {
  it('selects an insight via its card, toggling aria-pressed', async () => {
    const user = userEvent.setup()
    await renderWorkspace()

    const insightCard = screen.getByRole('button', { name: /Payment provider changes are a recurring precursor/ })
    expect(insightCard).toHaveAttribute('aria-pressed', 'false')

    await user.click(insightCard)
    expect(insightCard).toHaveAttribute('aria-pressed', 'true')
  })

  it('never renders a critical- or warning-toned element distinguishing it from Strategic Opportunities', async () => {
    const { container } = await renderWorkspace()

    expect(container.querySelectorAll('[class*="critical"]')).toHaveLength(0)
    expect(container.querySelectorAll('[class*="warning"]')).toHaveLength(0)
  })
})
