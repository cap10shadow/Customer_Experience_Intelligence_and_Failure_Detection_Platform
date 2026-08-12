import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'

import { AnalyticsWorkspace } from '@/workspaces/analytics'
import type { AnalyticsApiResponse } from '@/workspaces/analytics/api'

const SAMPLE_ANALYTICS_RESPONSE: AnalyticsApiResponse = {
  period: 'Last 30 Days',
  volumeTrend: [
    { date: '2026-08-07', count: 15 },
    { date: '2026-08-08', count: 20 },
  ],
  categoryTrend: [{ category: 'billing', count: 18 }],
  regionTrend: [{ region: 'EMEA', count: 12 }],
  sentimentTrend: [{ date: '2026-08-08', averageScore: 0.2, labelCounts: { positive: 5 } }],
  urgencyTrend: [{ urgency: 'high', count: 7 }],
  warnings: [],
}

function jsonResponse(body: unknown, status = 200) {
  return { status, ok: status >= 200 && status < 300, text: async () => JSON.stringify(body) } as Response
}

function mountWorkspace() {
  return render(
    <MemoryRouter>
      <AnalyticsWorkspace />
    </MemoryRouter>,
  )
}

/**
 * AnalyticsWorkspace owns a real loading state, driven by an actual
 * Gateway fetch (Part 5), and passes it through the composed section
 * hierarchy -- so composition assertions that need loaded content wait
 * for that transition to finish, exactly as they would against a real
 * data load.
 */
async function renderWorkspace() {
  const utils = mountWorkspace()
  await waitFor(() => {
    expect(document.querySelectorAll('[aria-busy="true"]')).toHaveLength(0)
  })
  return utils
}

describe('AnalyticsWorkspace loading (real composition hierarchy)', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(SAMPLE_ANALYTICS_RESPONSE)))
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('starts every section busy and transitions to loaded content once the workspace load completes, without a static isLoading prop', async () => {
    mountWorkspace()

    // Immediately after mount: sections are busy and real content is
    // suppressed, driven by AnalyticsWorkspace's own state -- not a
    // hardcoded `isLoading` prop passed in by the test.
    expect(document.querySelectorAll('[aria-busy="true"]').length).toBeGreaterThan(0)
    expect(screen.queryAllByText('billing recorded 18 complaint(s) in the returned trend data.')).toHaveLength(0)

    await waitFor(() => {
      expect(document.querySelectorAll('[aria-busy="true"]')).toHaveLength(0)
    })

    // Appears twice by design -- once as Executive Overview's condensed
    // restatement (Step 7.X A-08, verbatim reuse of the same real trend
    // fact), once as Trend Analysis's own detailed card.
    expect(screen.getAllByText('billing recorded 18 complaint(s) in the returned trend data.')).toHaveLength(2)
  })
})

describe('AnalyticsWorkspace composition', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(SAMPLE_ANALYTICS_RESPONSE)))
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

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

  it('presents Pattern Discovery as an honest future-capability placeholder (Step 7.X G-02), not a fabricated narrative', async () => {
    await renderWorkspace()

    expect(screen.getByText('Pattern discovery is a future capability')).toBeInTheDocument()
    expect(screen.queryByText('Checkout-related complaints tend to recur around provider changes')).not.toBeInTheDocument()
    expect(screen.queryByRole('list', { name: /patterns/i })).not.toBeInTheDocument()
  })

  it('Pattern Discovery renders immediately, not tied to the Analytics fetch loading state', () => {
    mountWorkspace()

    // Unlike Trend Analysis/Executive Overview, Pattern Discovery has no
    // backend data dependency, so it must not show a busy/loading state
    // pretending to wait on the fetch (Step 7.X G-02 loading rule).
    expect(screen.getByText('Pattern discovery is a future capability')).toBeInTheDocument()
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

describe('Organizational Insights and Strategic Opportunities (Step 7.X G-02: honest placeholders)', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(SAMPLE_ANALYTICS_RESPONSE)))
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('Organizational Insights presents an honest future-capability placeholder, not the old fabricated conclusion', async () => {
    await renderWorkspace()

    expect(screen.getByText('Organizational insights are a future capability')).toBeInTheDocument()
    expect(
      screen.queryByText('Payment provider changes are a recurring precursor to checkout incidents'),
    ).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Payment provider changes/ })).not.toBeInTheDocument()
  })

  it('Strategic Opportunities presents an honest future-capability placeholder, not the old fabricated opportunities', async () => {
    await renderWorkspace()

    expect(screen.getByText('Strategic opportunity identification is a future capability')).toBeInTheDocument()
    expect(screen.queryByText('Review how payment provider changes are communicated internally')).not.toBeInTheDocument()
    expect(screen.queryByText('Consider investing in more granular checkout monitoring')).not.toBeInTheDocument()
  })

  it('never renders a critical- or warning-toned element distinguishing Organizational Insights from Strategic Opportunities', async () => {
    const { container } = await renderWorkspace()

    expect(container.querySelectorAll('[class*="critical"]')).toHaveLength(0)
    expect(container.querySelectorAll('[class*="warning"]')).toHaveLength(0)
  })

  it('Organizational Insights and Strategic Opportunities render immediately, not tied to the Analytics fetch loading state', () => {
    mountWorkspace()

    expect(screen.getByText('Organizational insights are a future capability')).toBeInTheDocument()
    expect(screen.getByText('Strategic opportunity identification is a future capability')).toBeInTheDocument()
  })
})
