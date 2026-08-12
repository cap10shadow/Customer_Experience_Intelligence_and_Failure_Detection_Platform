import { afterEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'

import { RecommendationsWorkspace } from '@/workspaces/recommendations'
import type { RecommendationApiResponse } from '@/workspaces/recommendations/api'

const RECOMMENDATION_ID = 'rec-42'
const INCIDENT_ID = 'incident-42'

const SAMPLE_RECOMMENDATION_RESPONSE: RecommendationApiResponse = {
  recommendationId: RECOMMENDATION_ID,
  incidentId: INCIDENT_ID,
  generationId: 'gen-1',
  category: 'escalate',
  priority: 'high',
  score: 88,
  action: 'Escalate to payments team',
  recommendationRationale: 'The timing aligns with a recent payment gateway change.',
  priorityRationale: 'High business impact warrants immediate attention.',
  supportingEvidence: [{ source: 'business_impact', description: 'Business impact overall severity is high', weight: 5 }],
  createdAt: '2026-08-08T01:05:00Z',
}

function jsonResponse(body: unknown, status = 200) {
  return { status, ok: status >= 200 && status < 300, text: async () => JSON.stringify(body) } as Response
}

function renderAtRecommendation(recommendationId: string) {
  return render(
    <MemoryRouter initialEntries={[`/recommendations/${recommendationId}`]}>
      <Routes>
        <Route path="/recommendations/:recommendationId" element={<RecommendationsWorkspace />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('Recommendation real routing + Gateway integration', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('shows a loading state, then renders real Gateway-sourced content for the routed recommendationId', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(SAMPLE_RECOMMENDATION_RESPONSE)))

    renderAtRecommendation(RECOMMENDATION_ID)

    expect(document.querySelectorAll('[aria-busy="true"]').length).toBeGreaterThan(0)
    expect(screen.queryByText('Escalate to payments team')).not.toBeInTheDocument()

    await waitFor(() => expect(screen.getByText('Escalate to payments team')).toBeInTheDocument())

    // The same real recommendation_rationale text legitimately appears in
    // both Overview's summary and Rationale's explanation (Part 4's field
    // audit found only two real explanatory fields on the backend).
    expect(screen.getAllByText('The timing aligns with a recent payment gateway change.')).toHaveLength(2)
    expect(screen.getByText('High business impact warrants immediate attention.')).toBeInTheDocument()
    expect(screen.getByText('Escalate')).toBeInTheDocument()
    expect(screen.getByText('High priority')).toBeInTheDocument()
  })

  it('requests the routed recommendationId, never a raw backend service host', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(SAMPLE_RECOMMENDATION_RESPONSE)))

    renderAtRecommendation(RECOMMENDATION_ID)

    await waitFor(() => expect(fetch).toHaveBeenCalled())

    const [requestedUrl] = vi.mocked(fetch).mock.calls[0]
    const url = String(requestedUrl)
    expect(url).toContain(`/recommendations/${RECOMMENDATION_ID}`)
    expect(url).not.toMatch(/:800[1-8]/)
  })

  it('preserves recommendationId end-to-end: different routes request different recommendations', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(SAMPLE_RECOMMENDATION_RESPONSE)))

    renderAtRecommendation('another-recommendation-id')

    await waitFor(() => expect(fetch).toHaveBeenCalled())
    const [requestedUrl] = vi.mocked(fetch).mock.calls[0]
    expect(String(requestedUrl)).toContain('/recommendations/another-recommendation-id')
  })

  it('preserves incidentId as traceability metadata -- the Rationale section links to the real Incident, not an illustrative one', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(SAMPLE_RECOMMENDATION_RESPONSE)))

    renderAtRecommendation(RECOMMENDATION_ID)

    await waitFor(() => expect(screen.getByText('Escalate to payments team')).toBeInTheDocument())

    const link = screen.getByRole('link', { name: /Review the full investigation/ })
    expect(link).toHaveAttribute('href', `/investigations/${INCIDENT_ID}`)
  })

  it('never fabricates a decision, lifecycle, confidence, alternatives, risk, or outcome for real data', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(SAMPLE_RECOMMENDATION_RESPONSE)))

    renderAtRecommendation(RECOMMENDATION_ID)

    await waitFor(() => expect(screen.getByText('Escalate to payments team')).toBeInTheDocument())

    // Future-capability placeholders remain, never replaced by fabricated data for a real recommendation.
    expect(screen.getByText('Alternative option comparison is a future capability')).toBeInTheDocument()
    expect(screen.getByText('Expected outcome tracking is a future capability')).toBeInTheDocument()
    expect(screen.getByText('Risk assessment is a future capability')).toBeInTheDocument()

    // No approval/rejection/workflow controls anywhere.
    expect(screen.queryByRole('button', { name: /approve/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /reject/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /defer/i })).not.toBeInTheDocument()

    // Decision remains the honest, illustrative Pending Review state -- not a fabricated backend decision.
    // (Appears twice: the persistent Navigator reference and the Decision section itself.)
    expect(screen.getAllByText('Pending Review').length).toBeGreaterThan(0)
  })

  it('routes a 404 (recommendation genuinely not found) into the Recommendation error boundaries', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        jsonResponse({ error: { code: 'RESOURCE_NOT_FOUND', message: 'Recommendation was not found.', requestId: 'req-1' } }, 404),
      ),
    )

    renderAtRecommendation(RECOMMENDATION_ID)

    await waitFor(() => expect(screen.getAllByText(/Something went wrong loading/).length).toBeGreaterThan(0))
    expect(screen.getAllByText(/Recommendation was not found\./).length).toBeGreaterThan(0)

    // Sections independent of the fetch (no real data dependency) still render normally.
    expect(screen.getByText('Alternative option comparison is a future capability')).toBeInTheDocument()
  })

  it('routes a downstream Gateway failure into the Recommendation error boundaries', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        jsonResponse(
          { error: { code: 'DOWNSTREAM_SERVICE_UNAVAILABLE', message: 'The recommendation data could not be retrieved.', requestId: 'req-1' } },
          503,
        ),
      ),
    )

    renderAtRecommendation(RECOMMENDATION_ID)

    await waitFor(() => expect(screen.getAllByText(/Something went wrong loading/).length).toBeGreaterThan(0))
  })

  it('Part 7: retry issues a genuine new GET /api/v1/recommendations/:recommendationId request, and both sibling sections recover together', async () => {
    const user = userEvent.setup()
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        jsonResponse({ error: { code: 'DOWNSTREAM_SERVICE_UNAVAILABLE', message: 'Unavailable.', requestId: 'req-1' } }, 503),
      )
      .mockResolvedValueOnce(jsonResponse(SAMPLE_RECOMMENDATION_RESPONSE))
    vi.stubGlobal('fetch', fetchMock)

    renderAtRecommendation(RECOMMENDATION_ID)

    await waitFor(() => expect(screen.getAllByText(/Something went wrong loading/).length).toBeGreaterThan(0))
    expect(fetchMock).toHaveBeenCalledTimes(1)

    const retryButtons = screen.getAllByRole('button', { name: 'Try again' })
    await user.click(retryButtons[0])

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2))
    await waitFor(() => expect(screen.getByText('Escalate to payments team')).toBeInTheDocument())
    expect(screen.queryByText(/Something went wrong loading/)).not.toBeInTheDocument()
  })

  it('Part 7: a failed retry leaves the error UI correctly visible rather than silently clearing', async () => {
    const user = userEvent.setup()
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({ error: { code: 'DOWNSTREAM_SERVICE_UNAVAILABLE', message: 'Still unavailable.', requestId: 'req-1' } }, 503),
    )
    vi.stubGlobal('fetch', fetchMock)

    renderAtRecommendation(RECOMMENDATION_ID)

    await waitFor(() => expect(screen.getAllByText(/Something went wrong loading/).length).toBeGreaterThan(0))
    expect(fetchMock).toHaveBeenCalledTimes(1)

    const retryButtons = screen.getAllByRole('button', { name: 'Try again' })
    await user.click(retryButtons[0])

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2))
    expect(screen.getAllByText(/Something went wrong loading/).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/Still unavailable\./).length).toBeGreaterThan(0)
  })
})
