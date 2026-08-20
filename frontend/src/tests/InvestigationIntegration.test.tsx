import { afterEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'

import { InvestigationsWorkspace } from '@/workspaces/investigations'
import type { InvestigationApiResponse } from '@/workspaces/investigations/api'

const INCIDENT_ID = 'incident-42'

const DATASET_ID = 'dataset-1'

const SAMPLE_INVESTIGATION_RESPONSE: InvestigationApiResponse = {
  incidentId: INCIDENT_ID,
  datasetId: DATASET_ID,
  datasetVersionId: 'version-1',
  observation: {
    headline: 'Checkout failures rising',
    description: 'Payment failures are trending above baseline.',
  },
  evidence: [
    { id: 'a-1', headline: 'Checkout failures registered as an anomaly', detail: 'Triggered rule: percentage_change.', source: 'Anomaly Detection' },
    { id: 'a-2', headline: 'A second related anomaly was detected', detail: 'Triggered rule: regional_spike.', source: 'Anomaly Detection' },
    { id: 'incident-42-correlation', headline: '2 related anomalies were grouped into this incident', detail: 'Payment failures are trending above baseline.', source: 'Incident Correlation' },
  ],
  rootCause: {
    headline: 'Most likely cause: Payment Gateway Failure',
    reasoning: 'The timing aligns with a recent payment gateway change.',
    confidenceLevel: 'high',
    status: 'identified',
  },
  businessImpact: [
    { dimension: 'financial', headline: 'Significant impact detected', detail: 'Financial impact assessed as high.' },
    { dimension: 'customer', headline: 'Significant impact detected', detail: 'Customer impact assessed as high.' },
    { dimension: 'operational', headline: 'Moderate impact detected', detail: 'Operational impact assessed as medium.' },
    { dimension: 'sla', headline: 'Moderate impact detected', detail: 'Sla impact assessed as medium.' },
    { dimension: 'reputation', headline: 'Limited impact detected', detail: 'Reputation impact assessed as low.' },
  ],
  businessImpactConfidenceLevel: 'high',
  recommendedNextStep: {
    headline: 'Escalate to payments team',
    reason: 'Escalate recommendation (score 88).',
    recommendationId: 'rec-1',
  },
  warnings: [],
}

function jsonResponse(body: unknown, status = 200) {
  return { status, ok: status >= 200 && status < 300, text: async () => JSON.stringify(body) } as Response
}

function renderAtIncident(incidentId: string) {
  return render(
    <MemoryRouter initialEntries={[`/investigations/${incidentId}`]}>
      <Routes>
        <Route path="/investigations/:incidentId" element={<InvestigationsWorkspace />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('Investigation real routing + Gateway integration', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('shows a loading state, then renders real Gateway-sourced content for the routed incidentId', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(SAMPLE_INVESTIGATION_RESPONSE)))

    renderAtIncident(INCIDENT_ID)

    expect(document.querySelectorAll('[aria-busy="true"]').length).toBeGreaterThan(0)
    expect(screen.queryByText('Escalate to payments team')).not.toBeInTheDocument()

    await waitFor(() => expect(screen.getByText('Checkout failures rising')).toBeInTheDocument())

    expect(screen.getByText('Payment failures are trending above baseline.')).toBeInTheDocument()
    expect(screen.getByText(/Payment Gateway Failure/)).toBeInTheDocument()
    ;['Financial', 'Customer', 'Operational', 'SLA', 'Reputation'].forEach((dimension) => {
      expect(screen.getByText(dimension)).toBeInTheDocument()
    })
    expect(screen.getByText('Escalate to payments team')).toBeInTheDocument()
  })

  it('shows the investigation\'s real datasetId when no dataset context is available (never silently omitted)', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(SAMPLE_INVESTIGATION_RESPONSE)))

    renderAtIncident(INCIDENT_ID)

    expect(await screen.findByText(new RegExp(`Dataset:.*${DATASET_ID}`))).toBeInTheDocument()
  })

  it('requests the routed incidentId, never a raw backend service host', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(SAMPLE_INVESTIGATION_RESPONSE)))

    renderAtIncident(INCIDENT_ID)

    await waitFor(() => expect(fetch).toHaveBeenCalled())

    const [requestedUrl] = vi.mocked(fetch).mock.calls[0]
    const url = String(requestedUrl)
    expect(url).toContain(`/v1/investigations/${INCIDENT_ID}`)
    expect(url).not.toMatch(/:800[1-8]/)
  })

  it('preserves incidentId end-to-end: different routes request different incidents', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(SAMPLE_INVESTIGATION_RESPONSE)))

    renderAtIncident('another-incident-id')

    await waitFor(() => expect(fetch).toHaveBeenCalled())
    const [requestedUrl] = vi.mocked(fetch).mock.calls[0]
    expect(String(requestedUrl)).toContain('/v1/investigations/another-incident-id')
  })

  it('renders honest empty states when root cause, business impact, and recommendation are all legitimately absent', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        jsonResponse({
          ...SAMPLE_INVESTIGATION_RESPONSE,
          rootCause: null,
          businessImpact: [],
          businessImpactConfidenceLevel: null,
          recommendedNextStep: null,
        }),
      ),
    )

    renderAtIncident(INCIDENT_ID)

    await waitFor(() => expect(screen.getByText('Root cause analysis has not been completed yet')).toBeInTheDocument())
    expect(screen.getByText('Business impact has not been assessed yet')).toBeInTheDocument()
    expect(screen.getByText('No recommendation has been generated yet')).toBeInTheDocument()
    // Observation and Evidence still render normally -- only the absent sections show an empty state.
    expect(screen.getByText('Checkout failures rising')).toBeInTheDocument()
  })

  it('ARB-008: renders Business Impact dimension cards but never a confidence presentation when businessImpactConfidenceLevel is null', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(jsonResponse({ ...SAMPLE_INVESTIGATION_RESPONSE, businessImpactConfidenceLevel: null })),
    )

    renderAtIncident(INCIDENT_ID)

    await waitFor(() => expect(screen.getByText('Financial')).toBeInTheDocument())
    // Dimension summaries render normally -- only the confidence line is withheld.
    ;['Customer', 'Operational', 'SLA', 'Reputation'].forEach((dimension) => {
      expect(screen.getByText(dimension)).toBeInTheDocument()
    })
    // Not silently relabeled as the illustrative default either -- if it
    // had been, this exact "high confidence, business impact" pairing
    // would appear (Root Cause's own, unrelated confidence presentation
    // legitimately still renders "High confidence — root cause rule
    // certainty" elsewhere on the page, so the assertion is scoped to
    // this specific pairing, not the word "High" alone).
    expect(screen.queryByText(/business impact data completeness/)).not.toBeInTheDocument()
  })

  it('renders a confidence presentation when businessImpactConfidenceLevel is genuinely provided', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(SAMPLE_INVESTIGATION_RESPONSE)))

    renderAtIncident(INCIDENT_ID)

    await waitFor(() => expect(screen.getByText(/business impact data completeness/)).toBeInTheDocument())
  })

  it('renders honest empty state when no evidence is available', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse({ ...SAMPLE_INVESTIGATION_RESPONSE, evidence: [] })))

    renderAtIncident(INCIDENT_ID)

    await waitFor(() => expect(screen.getByText('No evidence gathered yet')).toBeInTheDocument())
  })

  it('renders no partial-failure notice when warnings is empty', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(SAMPLE_INVESTIGATION_RESPONSE)))

    renderAtIncident(INCIDENT_ID)

    await waitFor(() => expect(screen.getByText('Checkout failures rising')).toBeInTheDocument())
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
  })

  it('renders the Gateway-provided warnings as a non-blocking notice, not a failure', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        jsonResponse({
          ...SAMPLE_INVESTIGATION_RESPONSE,
          warnings: [`Root cause for incident ${INCIDENT_ID} is temporarily unavailable.`],
        }),
      ),
    )

    renderAtIncident(INCIDENT_ID)

    await waitFor(() => expect(screen.getByText('Checkout failures rising')).toBeInTheDocument())
    expect(screen.getByRole('status')).toBeInTheDocument()
    expect(screen.getByText(`Root cause for incident ${INCIDENT_ID} is temporarily unavailable.`)).toBeInTheDocument()
    expect(screen.queryByText(/Something went wrong loading/)).not.toBeInTheDocument()
  })

  it('routes a 404 (incident genuinely not found) into the Investigation error boundaries', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        jsonResponse({ error: { code: 'RESOURCE_NOT_FOUND', message: 'Incident was not found.', requestId: 'req-1' } }, 404),
      ),
    )

    renderAtIncident(INCIDENT_ID)

    await waitFor(() => expect(screen.getAllByText(/Something went wrong loading/).length).toBeGreaterThan(0))
    expect(screen.getAllByText(/Incident was not found\./).length).toBeGreaterThan(0)
  })

  it('routes a downstream Gateway failure into the Investigation error boundaries', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        jsonResponse(
          { error: { code: 'DOWNSTREAM_SERVICE_UNAVAILABLE', message: 'The investigation data could not be retrieved.', requestId: 'req-1' } },
          503,
        ),
      ),
    )

    renderAtIncident(INCIDENT_ID)

    await waitFor(() => expect(screen.getAllByText(/Something went wrong loading/).length).toBeGreaterThan(0))
  })

  it('Part 7: retry issues a genuine new GET /api/v1/investigations/:incidentId request, and ALL sibling sections recover together, not just the one whose retry was clicked', async () => {
    const user = userEvent.setup()
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        jsonResponse({ error: { code: 'DOWNSTREAM_SERVICE_UNAVAILABLE', message: 'Unavailable.', requestId: 'req-1' } }, 503),
      )
      .mockResolvedValueOnce(jsonResponse(SAMPLE_INVESTIGATION_RESPONSE))
    vi.stubGlobal('fetch', fetchMock)

    renderAtIncident(INCIDENT_ID)

    await waitFor(() => expect(screen.getAllByText(/Something went wrong loading/).length).toBeGreaterThan(0))
    expect(fetchMock).toHaveBeenCalledTimes(1)

    // Only the FIRST section's retry button is clicked -- proving the fix
    // is not "click every button," it's that one shared fetch recovers
    // every sibling section.
    const retryButtons = screen.getAllByRole('button', { name: 'Try again' })
    await user.click(retryButtons[0])

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2))
    await waitFor(() => expect(screen.getByText('Checkout failures rising')).toBeInTheDocument())
    expect(screen.getByText(/Payment Gateway Failure/)).toBeInTheDocument()
    expect(screen.getByText('Escalate to payments team')).toBeInTheDocument()
    expect(screen.queryByText(/Something went wrong loading/)).not.toBeInTheDocument()
  })

  it('Part 7: a failed retry leaves the error UI correctly visible rather than silently clearing', async () => {
    const user = userEvent.setup()
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({ error: { code: 'DOWNSTREAM_SERVICE_UNAVAILABLE', message: 'Still unavailable.', requestId: 'req-1' } }, 503),
    )
    vi.stubGlobal('fetch', fetchMock)

    renderAtIncident(INCIDENT_ID)

    await waitFor(() => expect(screen.getAllByText(/Something went wrong loading/).length).toBeGreaterThan(0))
    expect(fetchMock).toHaveBeenCalledTimes(1)

    const retryButtons = screen.getAllByRole('button', { name: 'Try again' })
    await user.click(retryButtons[0])

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2))
    expect(screen.getAllByText(/Something went wrong loading/).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/Still unavailable\./).length).toBeGreaterThan(0)
  })
})
