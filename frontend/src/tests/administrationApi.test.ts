import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { getIntelligenceConfiguration } from '@/workspaces/administration/api/administrationApi'
import { toIntelligenceConfigurationViewModel } from '@/workspaces/administration/api/viewModel'
import type { AdministrationApiIntelligenceConfigurationResponse } from '@/workspaces/administration/api/types'

function jsonResponse(body: unknown) {
  return { status: 200, ok: true, text: async () => JSON.stringify(body) } as Response
}

describe('administrationApi.getIntelligenceConfiguration', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse({ items: [] })))
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('requests GET /v1/administration/intelligence-configuration', async () => {
    await getIntelligenceConfiguration()

    const [requestedUrl, init] = vi.mocked(fetch).mock.calls[0]
    const url = new URL(String(requestedUrl))
    expect(url.pathname).toContain('/v1/administration/intelligence-configuration')
    expect(init?.method === 'GET' || init?.method === undefined).toBe(true)
  })
})

const SAMPLE_RESPONSE: AdministrationApiIntelligenceConfigurationResponse = {
  items: [
    {
      id: 'business-impact-weight-financial',
      name: 'Financial Impact Weight',
      whatItIs: 'The relative weight this dimension carries in the overall weighted business impact score.',
      governs: "Determines how much this dimension contributes to an Incident's overall business score.",
      currentValue: '35%',
    },
  ],
}

describe('toIntelligenceConfigurationViewModel', () => {
  it('maps real fetched items through unchanged -- no hardcoded frontend copy', () => {
    const viewModel = toIntelligenceConfigurationViewModel(SAMPLE_RESPONSE)
    expect(viewModel.items).toEqual(SAMPLE_RESPONSE.items)
  })

  it('never invents an item beyond what the response provides', () => {
    const viewModel = toIntelligenceConfigurationViewModel({ items: [] })
    expect(viewModel.items).toEqual([])
  })
})
