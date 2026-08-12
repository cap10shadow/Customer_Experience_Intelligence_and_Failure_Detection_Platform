import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'

import { DashboardWorkspace } from '@/workspaces/dashboard'
import type { DashboardApiResponse } from '@/workspaces/dashboard/api'

const SAMPLE_DASHBOARD_RESPONSE: DashboardApiResponse = {
  operationalBrief: {
    level: 'elevated',
    summary: '1 active incident(s); highest severity is high.',
    healthIndicators: [
      { id: 'complaint-volume', label: 'Complaint volume', level: 'elevated', trend: 'up', detail: '42 complaints on 2026-08-08, compared to 30 the prior day.' },
    ],
    criticalSituations: [{ id: 'incident-1', headline: 'Checkout failures rising', detail: 'Payment failures are trending above baseline.' }],
    keyChanges: [{ id: 'complaint-volume-change', headline: 'Complaint volume', direction: 'up', detail: '42 complaints on 2026-08-08, compared to 30 the prior day.' }],
    focusAreas: [],
  },
  decisionSummary: [
    {
      id: 'rec-1',
      headline: 'Escalate to payments team',
      importance: 'high',
      reason: 'Escalate recommendation for incident incident-1 (score 88).',
      nextDecision: 'Review this recommendation for the associated incident.',
      drillDownPath: '/recommendations/rec-1',
      drillDownLabel: 'Review recommendation',
    },
  ],
  investigationEntryPoints: [
    {
      id: 'incident-1',
      headline: 'Checkout failures rising',
      situation: 'Payment failures are trending above baseline.',
      significance: 'Severity: high; confidence: 82%.',
      direction: 'Most likely cause: Payment Provider Outage (confidence: high).',
      context: 'Business impact: high severity, high priority.',
      drillDownPath: '/investigations/incident-1',
      drillDownLabel: 'Investigate this story',
    },
  ],
  appliedFilters: { timeRange: 'current', region: null, businessUnit: null, productScope: null, userScope: null },
  warnings: [],
}

function jsonResponse(body: unknown, status = 200) {
  return { status, ok: status >= 200 && status < 300, text: async () => JSON.stringify(body) } as Response
}

function renderDashboard() {
  return render(
    <MemoryRouter>
      <DashboardWorkspace />
    </MemoryRouter>,
  )
}

describe('DashboardWorkspace composition', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(SAMPLE_DASHBOARD_RESPONSE)))
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('renders one workspace heading and the four architectural sections in fixed order', async () => {
    renderDashboard()

    expect(screen.getByRole('heading', { level: 1, name: 'Operational Intelligence Dashboard' })).toBeInTheDocument()

    const sectionHeadings = screen.getAllByRole('heading', { level: 2 }).map((heading) => heading.textContent)
    expect(sectionHeadings).toEqual([
      'Operational brief',
      'Decision summary',
      'Investigation entry points',
      'Supporting evidence',
    ])

    await waitFor(() => expect(screen.getByText('Escalate to payments team')).toBeInTheDocument())
  })

  it('renders every Operational Brief subsection as a nested level-3 heading', () => {
    renderDashboard()

    const subsectionHeadings = screen.getAllByRole('heading', { level: 3 }).map((heading) => heading.textContent)
    expect(subsectionHeadings).toEqual(
      expect.arrayContaining([
        'Overall operational status',
        'Critical situations',
        'Key changes',
        'Recommended focus',
        'Operational health snapshot',
      ]),
    )
  })

  it('shows a loading state before the Gateway response resolves, then real Gateway-sourced content', async () => {
    renderDashboard()

    expect(document.querySelectorAll('[aria-busy="true"]').length).toBeGreaterThan(0)
    expect(screen.queryByText('Escalate to payments team')).not.toBeInTheDocument()

    await waitFor(() => expect(screen.getByText('Escalate to payments team')).toBeInTheDocument())

    expect(screen.getByText('1 active incident(s); highest severity is high.')).toBeInTheDocument()
    // Appears twice: once as a Critical Situation, once as an Operational Story headline.
    expect(screen.getAllByText('Checkout failures rising').length).toBeGreaterThan(0)
  })

  it('surfaces Decision Opportunities as judgment calls, described only from real recommendation fields, drilling into the canonical Recommendation route', async () => {
    renderDashboard()

    await waitFor(() => expect(screen.getByRole('heading', { name: 'Escalate to payments team' })).toBeInTheDocument())
    expect(screen.getByText(/High business importance/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Review recommendation/ })).toHaveAttribute('href', '/recommendations/rec-1')

    // P1-1: Decision Summary must never claim a lifecycle/approval state.
    const forbiddenPhrases = [/awaiting approval/i, /pending decision/i, /\bapproved\b/i, /\brejected\b/i, /\bdeferred\b/i, /decision owner/i]
    forbiddenPhrases.forEach((phrase) => {
      expect(screen.queryByText(phrase)).not.toBeInTheDocument()
    })
  })

  it('presents Investigation Entry Points as Operational Stories with a drill-down to the canonical Investigation route', async () => {
    renderDashboard()

    await waitFor(() => expect(screen.getByRole('heading', { name: 'Checkout failures rising' })).toBeInTheDocument())
    expect(screen.getByRole('link', { name: /Investigate this story/ })).toHaveAttribute('href', '/investigations/incident-1')
  })

  it('presents Supporting Evidence as organized future-analytics placeholders, untouched by the Dashboard API', async () => {
    renderDashboard()

    expect(screen.getByText('Operational trends')).toBeInTheDocument()
    expect(screen.getByText('Regional comparison')).toBeInTheDocument()
    expect(screen.getByText('Sentiment trend')).toBeInTheDocument()
    await waitFor(() => expect(screen.getByText('Escalate to payments team')).toBeInTheDocument())
  })

  it('separates every section with a visible boundary, reinforcing one continuous journey', () => {
    renderDashboard()
    expect(document.querySelectorAll('hr').length).toBe(3)
  })

  it('requests only the Gateway base path, never a raw backend service host', async () => {
    renderDashboard()

    await waitFor(() => expect(fetch).toHaveBeenCalled())

    const [requestedUrl] = vi.mocked(fetch).mock.calls[0]
    const url = String(requestedUrl)
    expect(url).toContain('/dashboard')
    expect(url).not.toMatch(/:800[1-8]/)
  })
})

describe('DashboardWorkspace partial-failure warnings', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('renders no partial-failure notice when warnings is empty', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(SAMPLE_DASHBOARD_RESPONSE)))

    renderDashboard()

    await waitFor(() => expect(screen.getByText('Escalate to payments team')).toBeInTheDocument())
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
  })

  it('renders the Gateway-provided warnings as a non-blocking notice, not a failure', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        jsonResponse({
          ...SAMPLE_DASHBOARD_RESPONSE,
          warnings: ['Complaint volume trend is temporarily unavailable.'],
        }),
      ),
    )

    renderDashboard()

    await waitFor(() => expect(screen.getByText('Escalate to payments team')).toBeInTheDocument())
    expect(screen.getByRole('status')).toBeInTheDocument()
    expect(screen.getByText('Complaint volume trend is temporarily unavailable.')).toBeInTheDocument()
    // A warning is a partial success, not a section failure.
    expect(screen.queryByText(/Something went wrong loading/)).not.toBeInTheDocument()
  })
})

describe('DashboardWorkspace empty results', () => {
  it('renders honest empty states when the Gateway returns no incidents/recommendations', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        jsonResponse({
          ...SAMPLE_DASHBOARD_RESPONSE,
          operationalBrief: { level: 'stable', summary: 'No active incidents detected.', healthIndicators: [], criticalSituations: [], keyChanges: [], focusAreas: [] },
          decisionSummary: [],
          investigationEntryPoints: [],
        }),
      ),
    )

    renderDashboard()

    await waitFor(() => expect(screen.getByText('No decisions require attention')).toBeInTheDocument())
    expect(screen.getByText('No operational stories currently need investigation')).toBeInTheDocument()
    expect(screen.getByText('No critical situations')).toBeInTheDocument()
    expect(screen.getByText('No meaningful changes')).toBeInTheDocument()

    vi.unstubAllGlobals()
  })
})

describe('DashboardWorkspace failure handling', () => {
  it('routes a Gateway failure into each data-backed section\'s existing ErrorBoundary, leaving Supporting Evidence unaffected', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        jsonResponse(
          { error: { code: 'DOWNSTREAM_SERVICE_UNAVAILABLE', message: 'The dashboard data could not be retrieved.', requestId: 'req-1' } },
          503,
        ),
      ),
    )

    renderDashboard()

    await waitFor(() => expect(screen.getAllByText(/Something went wrong loading/).length).toBeGreaterThan(0))
    expect(screen.getAllByText(/The dashboard data could not be retrieved\./).length).toBeGreaterThan(0)

    // Supporting Evidence does not depend on the failed fetch at all.
    expect(screen.getByText('Operational trends')).toBeInTheDocument()

    vi.unstubAllGlobals()
  })

  it('Part 7: retry issues a genuine new GET /api/v1/dashboard request and renders real data on success', async () => {
    const user = userEvent.setup()
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        jsonResponse({ error: { code: 'DOWNSTREAM_SERVICE_UNAVAILABLE', message: 'Unavailable.', requestId: 'req-1' } }, 503),
      )
      .mockResolvedValueOnce(jsonResponse(SAMPLE_DASHBOARD_RESPONSE))
    vi.stubGlobal('fetch', fetchMock)

    renderDashboard()

    await waitFor(() => expect(screen.getAllByText(/Something went wrong loading/).length).toBeGreaterThan(0))
    expect(fetchMock).toHaveBeenCalledTimes(1)

    const retryButtons = screen.getAllByRole('button', { name: 'Try again' })
    await user.click(retryButtons[0])

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2))
    await waitFor(() => expect(screen.getByText('Escalate to payments team')).toBeInTheDocument())
    expect(screen.queryByText(/Something went wrong loading/)).not.toBeInTheDocument()

    vi.unstubAllGlobals()
  })

  it('Part 7: a failed retry leaves the error UI correctly visible rather than silently clearing', async () => {
    const user = userEvent.setup()
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({ error: { code: 'DOWNSTREAM_SERVICE_UNAVAILABLE', message: 'Still unavailable.', requestId: 'req-1' } }, 503),
    )
    vi.stubGlobal('fetch', fetchMock)

    renderDashboard()

    await waitFor(() => expect(screen.getAllByText(/Something went wrong loading/).length).toBeGreaterThan(0))
    expect(fetchMock).toHaveBeenCalledTimes(1)

    const retryButtons = screen.getAllByRole('button', { name: 'Try again' })
    await user.click(retryButtons[0])

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2))
    expect(screen.getAllByText(/Something went wrong loading/).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/Still unavailable\./).length).toBeGreaterThan(0)

    vi.unstubAllGlobals()
  })
})
