import { afterEach, describe, expect, it, vi } from 'vitest'
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
  categoryTrend: [
    { category: 'billing', count: 18 },
    { category: 'shipping', count: 9 },
  ],
  regionTrend: [{ region: 'EMEA', count: 12 }],
  sentimentTrend: [{ date: '2026-08-08', averageScore: 0.2, labelCounts: { positive: 5, neutral: 3 } }],
  urgencyTrend: [{ urgency: 'high', count: 7 }],
  warnings: [],
}

function jsonResponse(body: unknown, status = 200) {
  return { status, ok: status >= 200 && status < 300, text: async () => JSON.stringify(body) } as Response
}

function renderWorkspace() {
  return render(
    <MemoryRouter>
      <AnalyticsWorkspace />
    </MemoryRouter>,
  )
}

async function waitForLoaded() {
  await waitFor(() => expect(document.querySelectorAll('[aria-busy="true"]')).toHaveLength(0))
}

describe('Analytics real Gateway integration', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('requests /analytics/trends, never a raw backend service host', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(SAMPLE_ANALYTICS_RESPONSE)))

    renderWorkspace()
    await waitFor(() => expect(fetch).toHaveBeenCalled())

    const [requestedUrl] = vi.mocked(fetch).mock.calls[0]
    const url = String(requestedUrl)
    expect(url).toContain('/analytics/trends')
    expect(url).not.toMatch(/:800[1-8]/)
  })

  it('renders real Gateway-sourced Trend Analysis narratives, built only from real numbers', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(SAMPLE_ANALYTICS_RESPONSE)))

    renderWorkspace()
    await waitForLoaded()

    // Appears in both Trend Analysis (detail) and Executive Overview
    // (Step 7.X A-08's verbatim restatement of the same real fact).
    expect(screen.getAllByText(/20 complaint\(s\) were recorded on 2026-08-08/).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/billing recorded 18 complaint\(s\) in the returned trend data/).length).toBeGreaterThan(0)
  })

  it('never uses comparative or ranking language anywhere in the rendered Trend Analysis section', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(SAMPLE_ANALYTICS_RESPONSE)))

    renderWorkspace()
    await waitForLoaded()

    const trendHeading = screen.getByRole('heading', { level: 2, name: 'Trend Analysis' })
    const trendSection = trendHeading.closest('section')
    expect(trendSection).not.toBeNull()
    expect(trendSection?.textContent).not.toMatch(
      /\bmost common\b|\bhighest\b|\blowest\b|\bdominant\b|\bsignificant\b|\bconcerning\b|\bimproving\b|\bworsening\b|\bindicates\b|\bsuggests\b|\bdriven by\b|\bcorrelated with\b/i,
    )
  })

  it('re-fetches with the mapped days window when the analysis period changes', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(SAMPLE_ANALYTICS_RESPONSE))
    vi.stubGlobal('fetch', fetchMock)

    renderWorkspace()
    await waitForLoaded()

    const [firstUrl] = fetchMock.mock.calls[0]
    expect(new URL(String(firstUrl)).searchParams.get('period')).toBe('last-30-days')
  })

  it('renders an honest empty state in Trend Analysis when every real trend array is empty, rather than fabricating data', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        jsonResponse({
          period: 'Last 30 Days',
          volumeTrend: [],
          categoryTrend: [],
          regionTrend: [],
          sentimentTrend: [],
          urgencyTrend: [],
          warnings: [],
        }),
      ),
    )

    renderWorkspace()
    await waitForLoaded()

    expect(screen.getByText('No trend data recorded yet')).toBeInTheDocument()
  })

  it('routes a downstream Gateway failure into both real sections (Trend Analysis and Executive Overview) -- the four placeholder sections keep rendering', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        jsonResponse({ error: { code: 'DOWNSTREAM_SERVICE_FAILURE', message: 'Trend data could not be retrieved.', requestId: 'req-1' } }, 502),
      ),
    )

    renderWorkspace()
    await waitForLoaded()

    // Both Trend Analysis and Executive Overview (Step 7.X A-08) share
    // the same real fetch, so both show the error fallback.
    expect(screen.getByText(/Something went wrong loading the Trend Analysis/)).toBeInTheDocument()
    expect(screen.getByText(/Something went wrong loading the Executive Overview/)).toBeInTheDocument()
    expect(screen.getAllByText(/Trend data could not be retrieved\./).length).toBe(2)

    // Sections with no real backend capability are unaffected by the fetch failure.
    expect(screen.getByText('Pattern discovery is a future capability')).toBeInTheDocument()
    expect(screen.getByText('Recommendation effectiveness is a future capability')).toBeInTheDocument()
    expect(screen.getByText('Organizational insights are a future capability')).toBeInTheDocument()
    expect(screen.getByText('Strategic opportunity identification is a future capability')).toBeInTheDocument()
  })

  it('routes a downstream timeout the same way as any other Gateway failure', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        jsonResponse({ error: { code: 'DOWNSTREAM_TIMEOUT', message: 'The request to anomaly_service timed out.', requestId: 'req-1' } }, 504),
      ),
    )

    renderWorkspace()
    await waitForLoaded()

    expect(screen.getByText(/Something went wrong loading the Trend Analysis/)).toBeInTheDocument()
  })

  it('Part 7: retry issues a genuine new GET /api/v1/analytics/trends request and renders real data on success', async () => {
    const user = userEvent.setup()
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        jsonResponse({ error: { code: 'DOWNSTREAM_SERVICE_FAILURE', message: 'Trend data could not be retrieved.', requestId: 'req-1' } }, 502),
      )
      .mockResolvedValueOnce(jsonResponse(SAMPLE_ANALYTICS_RESPONSE))
    vi.stubGlobal('fetch', fetchMock)

    renderWorkspace()
    await waitForLoaded()
    expect(screen.getByText(/Something went wrong loading the Trend Analysis/)).toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledTimes(1)

    // Trend Analysis and Executive Overview (Step 7.X A-08) share the one
    // fetch, so both show their own "Try again" -- clicking either one
    // retries the same shared request.
    const retryButtons = screen.getAllByRole('button', { name: 'Try again' })
    await user.click(retryButtons[0])

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2))
    await waitFor(() => expect(screen.getAllByText(/20 complaint\(s\) were recorded on 2026-08-08/).length).toBeGreaterThan(0))
    expect(screen.queryByText(/Something went wrong loading the Trend Analysis/)).not.toBeInTheDocument()
    expect(screen.queryByText(/Something went wrong loading the Executive Overview/)).not.toBeInTheDocument()
  })

  it('Part 7: a failed retry leaves the Trend Analysis error UI correctly visible rather than silently clearing', async () => {
    const user = userEvent.setup()
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({ error: { code: 'DOWNSTREAM_SERVICE_FAILURE', message: 'Still unavailable.', requestId: 'req-1' } }, 502),
    )
    vi.stubGlobal('fetch', fetchMock)

    renderWorkspace()
    await waitForLoaded()
    expect(fetchMock).toHaveBeenCalledTimes(1)

    const retryButtons = screen.getAllByRole('button', { name: 'Try again' })
    await user.click(retryButtons[0])

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2))
    expect(screen.getByText(/Something went wrong loading the Trend Analysis/)).toBeInTheDocument()
    expect(screen.getAllByText(/Still unavailable\./).length).toBe(2)
  })
})

describe('Analytics architecture regression protection', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('never fabricates Pattern Discovery, Recommendation Effectiveness, Organizational Insights, or Strategic Opportunities from real Trend data (Step 7.X G-02)', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(SAMPLE_ANALYTICS_RESPONSE)))

    renderWorkspace()
    await waitForLoaded()

    // All four render an honest future-capability placeholder, unaffected
    // by real Trend data -- never a narrative/insight/opportunity derived
    // (or left over) from it.
    expect(screen.getByText('Pattern discovery is a future capability')).toBeInTheDocument()
    expect(screen.getByText('Recommendation effectiveness is a future capability')).toBeInTheDocument()
    expect(screen.getByText('Organizational insights are a future capability')).toBeInTheDocument()
    expect(screen.getByText('Strategic opportunity identification is a future capability')).toBeInTheDocument()

    expect(screen.queryByText('Checkout-related complaints tend to recur around provider changes')).not.toBeInTheDocument()
    expect(screen.queryByText(/Payment provider changes are a recurring precursor/)).not.toBeInTheDocument()
    expect(screen.queryByText('Review how payment provider changes are communicated internally')).not.toBeInTheDocument()
  })

  it('never introduces recommendation approval, lifecycle, outcome tracking, alerting, or incident-management controls', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(SAMPLE_ANALYTICS_RESPONSE)))

    renderWorkspace()
    await waitForLoaded()

    expect(screen.queryByRole('button', { name: /approve/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /assign/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /reject/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /defer/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /acknowledge/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('keeps the Scope Indicator singular even after a real data load (UX-005)', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(SAMPLE_ANALYTICS_RESPONSE)))

    renderWorkspace()
    await waitForLoaded()

    expect(screen.getAllByText('Last 30 days')).toHaveLength(1)
  })
})
