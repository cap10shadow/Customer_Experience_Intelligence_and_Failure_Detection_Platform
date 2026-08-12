import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { getInvestigation } from '@/workspaces/investigations/api/investigationApi'
import { toInvestigationViewModel } from '@/workspaces/investigations/api/viewModel'
import type { InvestigationApiResponse } from '@/workspaces/investigations/api/types'

function jsonResponse(body: unknown) {
  return { status: 200, ok: true, text: async () => JSON.stringify(body) } as Response
}

describe('investigationApi.getInvestigation', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse({})))
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('requests /investigations/:incidentId with the given incident id', async () => {
    await getInvestigation('incident-1')

    const [requestedUrl] = vi.mocked(fetch).mock.calls[0]
    const url = new URL(String(requestedUrl))
    expect(url.pathname).toContain('/investigations/incident-1')
  })

  it('URL-encodes the incident id', async () => {
    await getInvestigation('incident/with slash')

    const [requestedUrl] = vi.mocked(fetch).mock.calls[0]
    expect(String(requestedUrl)).toContain(encodeURIComponent('incident/with slash'))
  })
})

describe('toInvestigationViewModel', () => {
  it('maps the Gateway InvestigationResponse into the workspace view model without inventing fields', () => {
    const response: InvestigationApiResponse = {
      incidentId: 'incident-1',
      observation: { headline: 'h', description: 'd' },
      evidence: [{ id: 'e-1', headline: 'h', detail: 'd', source: 'Anomaly Detection' }],
      rootCause: { headline: 'h', reasoning: 'r', confidenceLevel: 'high' },
      businessImpact: [{ dimension: 'financial', headline: 'h', detail: 'd' }],
      businessImpactConfidenceLevel: 'high',
      recommendedNextStep: { headline: 'h', reason: 'r', recommendationId: 'rec-1' },
      warnings: ['Business impact for incident incident-1 is temporarily unavailable. (DOWNSTREAM_SERVICE_UNAVAILABLE)'],
    }

    const viewModel = toInvestigationViewModel(response)

    expect(viewModel.observation).toBe(response.observation)
    expect(viewModel.evidence).toBe(response.evidence)
    expect(viewModel.rootCause).toBe(response.rootCause)
    expect(viewModel.businessImpact).toBe(response.businessImpact)
    expect(viewModel.businessImpactConfidenceLevel).toBe('high')
    expect(viewModel.recommendedNextStep).toBe(response.recommendedNextStep)
    expect(viewModel.warnings).toEqual(response.warnings)
  })

  it('preserves explicit null/empty legitimate-absence states rather than substituting defaults', () => {
    const response: InvestigationApiResponse = {
      incidentId: 'incident-1',
      observation: { headline: 'h', description: 'd' },
      evidence: [],
      rootCause: null,
      businessImpact: [],
      businessImpactConfidenceLevel: null,
      recommendedNextStep: null,
      warnings: [],
    }

    const viewModel = toInvestigationViewModel(response)

    expect(viewModel.rootCause).toBeNull()
    expect(viewModel.businessImpact).toEqual([])
    expect(viewModel.recommendedNextStep).toBeNull()
  })
})
