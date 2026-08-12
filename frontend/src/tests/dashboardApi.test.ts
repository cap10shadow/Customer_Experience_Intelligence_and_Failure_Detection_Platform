import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { getDashboard } from '@/workspaces/dashboard/api/dashboardApi'
import { toDashboardViewModel } from '@/workspaces/dashboard/api/viewModel'
import type { DashboardApiResponse } from '@/workspaces/dashboard/api/types'

function jsonResponse(body: unknown) {
  return { status: 200, ok: true, text: async () => JSON.stringify(body) } as Response
}

describe('dashboardApi.getDashboard', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse({})))
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('requests /dashboard with only the supplied timeRange query parameter', async () => {
    await getDashboard({ timeRange: '7d' })

    const [requestedUrl] = vi.mocked(fetch).mock.calls[0]
    const url = new URL(String(requestedUrl))
    expect(url.pathname).toContain('/dashboard')
    expect(url.searchParams.get('timeRange')).toBe('7d')
    expect(url.searchParams.has('region')).toBe(false)
    expect(url.searchParams.has('businessUnit')).toBe(false)
    expect(url.searchParams.has('productScope')).toBe(false)
    expect(url.searchParams.has('userScope')).toBe(false)
  })

  it('omits null/undefined scope fields from the query string rather than sending them as literal "null"', async () => {
    await getDashboard({ timeRange: 'current', region: null, businessUnit: undefined })

    const [requestedUrl] = vi.mocked(fetch).mock.calls[0]
    const url = new URL(String(requestedUrl))
    expect(url.searchParams.has('region')).toBe(false)
    expect(url.searchParams.has('businessUnit')).toBe(false)
  })

  it('forwards a real scope value when one is supplied', async () => {
    await getDashboard({ timeRange: 'current', region: 'EMEA' })

    const [requestedUrl] = vi.mocked(fetch).mock.calls[0]
    const url = new URL(String(requestedUrl))
    expect(url.searchParams.get('region')).toBe('EMEA')
  })
})

describe('toDashboardViewModel', () => {
  it('maps the Gateway DashboardResponse into the workspace view model without inventing fields', () => {
    const response: DashboardApiResponse = {
      operationalBrief: {
        level: 'critical',
        summary: '2 active incident(s); highest severity is critical.',
        healthIndicators: [{ id: 'x', label: 'X', level: 'critical', trend: 'up', detail: 'd' }],
        criticalSituations: [{ id: 'c1', headline: 'h', detail: 'd' }],
        keyChanges: [{ id: 'k1', headline: 'h', direction: 'up', detail: 'd' }],
        focusAreas: [],
      },
      decisionSummary: [
        {
          id: 'rec-1',
          headline: 'Escalate',
          importance: 'high',
          reason: 'r',
          nextDecision: 'Review this recommendation for the associated incident.',
          drillDownPath: '/recommendations',
          drillDownLabel: 'Review recommendation',
        },
      ],
      investigationEntryPoints: [
        {
          id: 'incident-1',
          headline: 'h',
          situation: 's',
          significance: 'sig',
          direction: 'dir',
          context: 'ctx',
          drillDownPath: '/investigations',
          drillDownLabel: 'Investigate this story',
        },
      ],
      appliedFilters: { timeRange: '7d', region: null, businessUnit: null, productScope: null, userScope: null },
      warnings: ['Recommendation data is temporarily unavailable. (DOWNSTREAM_SERVICE_UNAVAILABLE)'],
    }

    const viewModel = toDashboardViewModel(response)

    expect(viewModel.operationalStatus).toEqual({ level: 'critical', summary: '2 active incident(s); highest severity is critical.' })
    expect(viewModel.healthIndicators).toBe(response.operationalBrief.healthIndicators)
    expect(viewModel.criticalSituations).toBe(response.operationalBrief.criticalSituations)
    expect(viewModel.keyChanges).toBe(response.operationalBrief.keyChanges)
    expect(viewModel.focusAreas).toBe(response.operationalBrief.focusAreas)
    expect(viewModel.decisionOpportunities).toBe(response.decisionSummary)
    expect(viewModel.operationalStories).toBe(response.investigationEntryPoints)
    expect(viewModel.warnings).toEqual(response.warnings)
  })
})
