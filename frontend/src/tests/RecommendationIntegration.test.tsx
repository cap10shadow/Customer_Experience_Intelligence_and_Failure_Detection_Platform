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
  datasetId: 'dataset-1',
  datasetVersionId: 'version-1',
  generationId: 'gen-1',
  category: 'escalate',
  priority: 'high',
  score: 88,
  action: 'Escalate to payments team',
  recommendationRationale: 'The timing aligns with a recent payment gateway change.',
  priorityRationale: 'High business impact warrants immediate attention.',
  supportingEvidence: [{ source: 'business_impact', description: 'Business impact overall severity is high', weight: 5 }],
  createdAt: '2026-08-08T01:05:00Z',
  decision: null,
  decisionNote: null,
  decidedAt: null,
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

  it('shows the recommendation\'s real datasetId when no dataset context is available (never silently omitted)', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(SAMPLE_RECOMMENDATION_RESPONSE)))

    renderAtRecommendation(RECOMMENDATION_ID)

    expect(await screen.findByText(/Dataset:.*dataset-1/)).toBeInTheDocument()
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

  it('never fabricates a lifecycle, confidence, alternatives, risk, or outcome for real data, and shows no decision when none is persisted', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(SAMPLE_RECOMMENDATION_RESPONSE)))

    renderAtRecommendation(RECOMMENDATION_ID)

    await waitFor(() => expect(screen.getByText('Escalate to payments team')).toBeInTheDocument())

    // Future-capability placeholders remain, never replaced by fabricated data for a real recommendation.
    expect(screen.getByText('Alternative option comparison is a future capability')).toBeInTheDocument()
    expect(screen.getByText('Expected outcome tracking is a future capability')).toBeInTheDocument()
    expect(screen.getByText('Risk assessment is a future capability')).toBeInTheDocument()

    // Recommendation Lifecycle still has no real decision to gate on for this recommendation.
    expect(screen.getByText('Recommendation lifecycle tracking is a future capability')).toBeInTheDocument()
    expect(screen.getByText('Decision capability not yet available')).toBeInTheDocument()
    expect(screen.queryByText('Pending Review')).not.toBeInTheDocument()

    // The real Decision form (Step 7.X G-01) is present -- not a placeholder -- since a real recommendationId exists to submit against.
    expect(screen.getByRole('button', { name: /save decision/i })).toBeInTheDocument()
  })

  it('shows the real, persisted decision when the backend has one, reflected in both the section and the navigator status', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        jsonResponse({
          ...SAMPLE_RECOMMENDATION_RESPONSE,
          decision: 'approved',
          decisionNote: 'Reviewed and approved.',
          decidedAt: '2026-08-12T10:00:00Z',
        }),
      ),
    )

    renderAtRecommendation(RECOMMENDATION_ID)

    await waitFor(() => expect(screen.getByText('Escalate to payments team')).toBeInTheDocument())

    expect(screen.getByText('Reviewed and approved.')).toBeInTheDocument()
    const nav = screen.getByRole('navigation', { name: 'Recommendation sections' })
    expect(nav).toHaveTextContent('Approved')
  })

  it('submitting a decision issues a real PATCH and reflects the refetched, persisted state -- never an optimistic fabrication', async () => {
    const user = userEvent.setup()
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(SAMPLE_RECOMMENDATION_RESPONSE))
      .mockResolvedValueOnce(
        jsonResponse({
          ...SAMPLE_RECOMMENDATION_RESPONSE,
          decision: 'deferred',
          decisionNote: 'Need more information.',
          decidedAt: '2026-08-12T11:00:00Z',
        }),
      )
      .mockResolvedValueOnce(
        jsonResponse({
          ...SAMPLE_RECOMMENDATION_RESPONSE,
          decision: 'deferred',
          decisionNote: 'Need more information.',
          decidedAt: '2026-08-12T11:00:00Z',
        }),
      )
    vi.stubGlobal('fetch', fetchMock)

    renderAtRecommendation(RECOMMENDATION_ID)

    await waitFor(() => expect(screen.getByText('Escalate to payments team')).toBeInTheDocument())

    const select = screen.getByLabelText('Record a decision')
    await user.selectOptions(select, 'deferred')
    const noteField = screen.getByLabelText('Note (optional)')
    await user.type(noteField, 'Need more information.')
    await user.click(screen.getByRole('button', { name: /save decision/i }))

    await waitFor(() => expect(screen.getByText('Need more information.')).toBeInTheDocument())

    const [, patchInit] = fetchMock.mock.calls[1]
    expect(patchInit?.method).toBe('PATCH')
    expect(String(fetchMock.mock.calls[1][0])).toContain(`/recommendations/${RECOMMENDATION_ID}/decision`)
    expect(JSON.parse(String(patchInit?.body))).toEqual({ decision: 'deferred', note: 'Need more information.' })
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
