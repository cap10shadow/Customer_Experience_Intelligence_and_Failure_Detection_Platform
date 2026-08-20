import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { getRecommendation, patchRecommendationDecision } from '@/workspaces/recommendations/api/recommendationApi'
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

  it('requests /v1/recommendations/:recommendationId with the given recommendation id', async () => {
    await getRecommendation('rec-1')

    const [requestedUrl] = vi.mocked(fetch).mock.calls[0]
    const url = new URL(String(requestedUrl))
    expect(url.pathname).toContain('/v1/recommendations/rec-1')
  })

  it('URL-encodes the recommendation id', async () => {
    await getRecommendation('rec/with slash')

    const [requestedUrl] = vi.mocked(fetch).mock.calls[0]
    expect(String(requestedUrl)).toContain(encodeURIComponent('rec/with slash'))
  })
})

describe('recommendationApi.patchRecommendationDecision', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse({})))
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('issues a PATCH to /v1/recommendations/:recommendationId/decision with the decision and note', async () => {
    await patchRecommendationDecision('rec-1', 'approved', 'Looks correct.')

    const [requestedUrl, init] = vi.mocked(fetch).mock.calls[0]
    const url = new URL(String(requestedUrl))
    expect(url.pathname).toContain('/v1/recommendations/rec-1/decision')
    expect(init?.method).toBe('PATCH')
    expect(JSON.parse(String(init?.body))).toEqual({ decision: 'approved', note: 'Looks correct.' })
  })

  it('sends note as undefined when omitted, never a client-supplied decidedAt', async () => {
    await patchRecommendationDecision('rec-1', 'deferred', undefined)

    const [, init] = vi.mocked(fetch).mock.calls[0]
    const body = JSON.parse(String(init?.body))
    expect(body.decision).toBe('deferred')
    expect(body.note).toBeUndefined()
    expect(body.decidedAt).toBeUndefined()
    expect(body.actorId).toBeUndefined()
  })
})

const SAMPLE_RESPONSE: RecommendationApiResponse = {
  recommendationId: 'rec-1',
  incidentId: 'incident-1',
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

  it('never introduces a confidence, alternatives, risk, outcome, or lifecycle field', () => {
    const viewModel = toRecommendationViewModel(SAMPLE_RESPONSE)
    const forbiddenKeys = ['confidence', 'alternatives', 'risk', 'outcome', 'effectiveness', 'lifecycle']
    forbiddenKeys.forEach((key) => {
      expect(viewModel).not.toHaveProperty(key)
      expect(viewModel.overview).not.toHaveProperty(key)
      expect(viewModel.rationale).not.toHaveProperty(key)
    })
  })

  it('leaves decision undefined when the backend has never recorded one (Step 7.X G-01: never a fabricated pending-review default)', () => {
    const viewModel = toRecommendationViewModel(SAMPLE_RESPONSE)
    expect(viewModel.decision).toBeUndefined()
  })

  it('maps a real persisted decision, translating the backend "pending" value to the workspace\'s "pending-review" status', () => {
    const viewModel = toRecommendationViewModel({ ...SAMPLE_RESPONSE, decision: 'pending', decisionNote: null })
    expect(viewModel.decision).toEqual({ status: 'pending-review', note: '' })
  })

  it('maps approved/rejected/deferred decisions and their notes through unchanged', () => {
    const approved = toRecommendationViewModel({ ...SAMPLE_RESPONSE, decision: 'approved', decisionNote: 'Looks correct.' })
    expect(approved.decision).toEqual({ status: 'approved', note: 'Looks correct.' })

    const rejected = toRecommendationViewModel({ ...SAMPLE_RESPONSE, decision: 'rejected', decisionNote: null })
    expect(rejected.decision).toEqual({ status: 'rejected', note: '' })
  })

  it('never exposes an actor/owner field on the view model', () => {
    const viewModel = toRecommendationViewModel({ ...SAMPLE_RESPONSE, decision: 'approved', decisionNote: 'ok' })
    expect(viewModel).not.toHaveProperty('actorId')
    expect(viewModel).not.toHaveProperty('decidedBy')
    expect(viewModel).not.toHaveProperty('owner')
  })
})
