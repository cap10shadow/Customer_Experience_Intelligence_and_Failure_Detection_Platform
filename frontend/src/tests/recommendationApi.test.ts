import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { getRecommendation } from '@/workspaces/recommendations/api/recommendationApi'
import { toRecommendationViewModel } from '@/workspaces/recommendations/api/viewModel'
import type { RecommendationApiResponse } from '@/workspaces/recommendations/api/types'

function jsonResponse(body: unknown) {
  return { status: 200, ok: true, text: async () => JSON.stringify(body) } as Response
}

describe('recommendationApi.getRecommendation', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse({})))
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('requests /recommendations/:recommendationId with the given recommendation id', async () => {
    await getRecommendation('rec-1')

    const [requestedUrl] = vi.mocked(fetch).mock.calls[0]
    const url = new URL(String(requestedUrl))
    expect(url.pathname).toContain('/recommendations/rec-1')
  })

  it('URL-encodes the recommendation id', async () => {
    await getRecommendation('rec/with slash')

    const [requestedUrl] = vi.mocked(fetch).mock.calls[0]
    expect(String(requestedUrl)).toContain(encodeURIComponent('rec/with slash'))
  })
})

const SAMPLE_RESPONSE: RecommendationApiResponse = {
  recommendationId: 'rec-1',
  incidentId: 'incident-1',
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

describe('toRecommendationViewModel', () => {
  it('maps the Gateway RecommendationResponse into the workspace view model using only real backend fields', () => {
    const viewModel = toRecommendationViewModel(SAMPLE_RESPONSE)

    expect(viewModel.recommendationId).toBe('rec-1')
    expect(viewModel.incidentId).toBe('incident-1')
    expect(viewModel.overview).toEqual({
      headline: 'Escalate to payments team',
      summary: 'The timing aligns with a recent payment gateway change.',
      category: 'Escalate',
      priority: 'High',
    })
    expect(viewModel.rationale).toEqual({
      headline: 'High business impact warrants immediate attention.',
      explanation: 'The timing aligns with a recent payment gateway change.',
    })
  })

  it('title-cases multi-word category values without inventing new text', () => {
    const viewModel = toRecommendationViewModel({ ...SAMPLE_RESPONSE, category: 'customer_communication' })
    expect(viewModel.overview.category).toBe('Customer Communication')
  })

  it('never introduces a confidence, alternatives, risk, outcome, or decision/lifecycle field', () => {
    const viewModel = toRecommendationViewModel(SAMPLE_RESPONSE)
    const forbiddenKeys = [
      'confidence',
      'alternatives',
      'risk',
      'outcome',
      'effectiveness',
      'decision',
      'lifecycle',
      'status',
    ]
    forbiddenKeys.forEach((key) => {
      expect(viewModel).not.toHaveProperty(key)
      expect(viewModel.overview).not.toHaveProperty(key)
      expect(viewModel.rationale).not.toHaveProperty(key)
    })
  })
})
