import { afterEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'

import { AdministrationWorkspace } from '@/workspaces/administration'
import type { AdministrationApiOverviewResponse } from '@/workspaces/administration/api'

const SAMPLE_OVERVIEW_RESPONSE: AdministrationApiOverviewResponse = {
  services: [
    { id: 'gateway', name: 'Gateway Service', status: 'healthy', detail: 'ok' },
    { id: 'ingestion', name: 'Ingestion Service', status: 'healthy', detail: 'ok' },
    { id: 'nlp', name: 'NLP Service', status: 'healthy', detail: 'ok' },
    { id: 'anomaly', name: 'Anomaly Service', status: 'healthy', detail: 'ok' },
    { id: 'root_cause', name: 'Root Cause Service', status: 'healthy', detail: 'ok' },
    { id: 'business_impact', name: 'Business Impact Service', status: 'healthy', detail: 'ok' },
    { id: 'recommendation', name: 'Recommendation Service', status: 'healthy', detail: 'ok' },
    { id: 'copilot', name: 'Copilot Service', status: 'healthy', detail: 'ok' },
    { id: 'evaluation', name: 'Evaluation Service', status: 'healthy', detail: 'ok' },
  ],
  warnings: [],
}

const SAMPLE_INTELLIGENCE_CONFIGURATION_RESPONSE = { items: [] }

function jsonResponse(body: unknown, status = 200) {
  return { status, ok: status >= 200 && status < 300, text: async () => JSON.stringify(body) } as Response
}

/**
 * Stubs fetch for both Administration data sources (Platform Overview and
 * Intelligence Configuration, Step 7.X A-02/G-05) -- `overviewResponder`
 * controls only the `/administration/overview` call under test;
 * `/administration/intelligence-configuration` always resolves to a
 * minimal, valid, empty response so it never interferes with Platform
 * Overview assertions in this file.
 */
function stubAdministrationFetch(overviewResponse: unknown, overviewStatus = 200) {
  vi.stubGlobal(
    'fetch',
    vi.fn((input: RequestInfo | URL) => {
      const url = String(input)
      if (url.includes('/administration/intelligence-configuration')) {
        return Promise.resolve(jsonResponse(SAMPLE_INTELLIGENCE_CONFIGURATION_RESPONSE))
      }
      return Promise.resolve(jsonResponse(overviewResponse, overviewStatus))
    }),
  )
}

function renderWorkspace() {
  return render(
    <MemoryRouter>
      <AdministrationWorkspace />
    </MemoryRouter>,
  )
}

describe('Administration Platform Overview real Gateway integration (Step 7.X A-02)', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('shows a loading state, then renders real per-service health data', async () => {
    stubAdministrationFetch(SAMPLE_OVERVIEW_RESPONSE)

    renderWorkspace()

    expect(document.querySelectorAll('[aria-busy="true"]').length).toBeGreaterThan(0)
    expect(screen.queryByText('9/9 services healthy')).not.toBeInTheDocument()

    await waitFor(() => expect(screen.getByText('9/9 services healthy')).toBeInTheDocument())
    expect(screen.getByText('Gateway Service')).toBeInTheDocument()
    expect(screen.getByText('Recommendation Service')).toBeInTheDocument()
    expect(screen.getAllByText('Healthy').length).toBe(9)
  })

  it('requests only the Gateway base path, never a raw backend service host', async () => {
    stubAdministrationFetch(SAMPLE_OVERVIEW_RESPONSE)

    renderWorkspace()

    await waitFor(() => expect(fetch).toHaveBeenCalled())

    const requestedUrls = vi.mocked(fetch).mock.calls.map(([url]) => String(url))
    const overviewCall = requestedUrls.find((url) => url.includes('/administration/overview'))
    expect(overviewCall).toBeDefined()
    requestedUrls.forEach((url) => {
      expect(url).not.toMatch(/:800[1-8]/)
    })
  })

  it('reports a partial service-health failure honestly, without failing the whole section', async () => {
    stubAdministrationFetch({
      services: [
        ...SAMPLE_OVERVIEW_RESPONSE.services.filter((service) => service.id !== 'copilot'),
        { id: 'copilot', name: 'Copilot Service', status: 'unavailable', detail: 'DOWNSTREAM_SERVICE_UNAVAILABLE' },
      ],
      warnings: ['Copilot Service is unavailable (DOWNSTREAM_SERVICE_UNAVAILABLE).'],
    })

    renderWorkspace()

    await waitFor(() => expect(screen.getByText('8/9 services healthy')).toBeInTheDocument())
    expect(screen.getAllByText('Healthy').length).toBe(8)
    expect(screen.getAllByText('Unavailable').length).toBe(1)
    // The partial-failure warning is surfaced honestly, not silently dropped.
    expect(screen.getByRole('status')).toBeInTheDocument()
    expect(screen.getByText(/Copilot Service is unavailable/)).toBeInTheDocument()
    // A partial per-service failure is not a section failure.
    expect(screen.queryByText(/Something went wrong loading/)).not.toBeInTheDocument()
  })

  it('never invents a service status beyond the two real values (healthy/unavailable)', async () => {
    stubAdministrationFetch(SAMPLE_OVERVIEW_RESPONSE)

    renderWorkspace()

    await waitFor(() => expect(screen.getByText('9/9 services healthy')).toBeInTheDocument())
    expect(screen.queryByText(/degraded/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/operating normally/i)).not.toBeInTheDocument()
  })

  it('routes a complete Gateway failure into the Platform Overview ErrorBoundary, leaving the rest of Administration presentation-safe', async () => {
    stubAdministrationFetch(
      { error: { code: 'INTERNAL_ERROR', message: 'An unexpected error occurred.', requestId: 'req-1' } },
      500,
    )

    renderWorkspace()

    await waitFor(() => expect(screen.getAllByText(/Something went wrong loading/).length).toBeGreaterThan(0))
    // Every other section is untouched by Platform Overview's failure -- still six sections' worth of headings.
    const sectionHeadings = screen.getAllByRole('heading', { level: 2 }).map((heading) => heading.textContent)
    expect(sectionHeadings).toEqual(
      expect.arrayContaining([
        'User & Access Management',
        'Data Sources & Integrations',
        'Intelligence Configuration',
        'Platform Governance',
        'Audit & Change History',
      ]),
    )
    expect(screen.queryByRole('button', { name: /approve/i })).not.toBeInTheDocument()
  })

  it('Part 7-style retry: issues a genuine new GET /api/v1/administration/overview request and recovers', async () => {
    const user = userEvent.setup()
    let overviewCallCount = 0
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const url = String(input)
      if (url.includes('/administration/intelligence-configuration')) {
        return Promise.resolve(jsonResponse(SAMPLE_INTELLIGENCE_CONFIGURATION_RESPONSE))
      }
      overviewCallCount += 1
      if (overviewCallCount === 1) {
        return Promise.resolve(
          jsonResponse({ error: { code: 'DOWNSTREAM_SERVICE_UNAVAILABLE', message: 'Unavailable.', requestId: 'req-1' } }, 503),
        )
      }
      return Promise.resolve(jsonResponse(SAMPLE_OVERVIEW_RESPONSE))
    })
    vi.stubGlobal('fetch', fetchMock)

    renderWorkspace()

    await waitFor(() => expect(screen.getAllByText(/Something went wrong loading/).length).toBeGreaterThan(0))
    const retryButtons = screen.getAllByRole('button', { name: 'Try again' })
    await user.click(retryButtons[0])

    await waitFor(() => expect(screen.getByText('9/9 services healthy')).toBeInTheDocument())
    expect(screen.queryByText(/Something went wrong loading/)).not.toBeInTheDocument()
  })
})
