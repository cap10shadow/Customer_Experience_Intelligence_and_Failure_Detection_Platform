import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { getAnalytics } from '@/workspaces/analytics/api/analyticsApi'
import { toAnalyticsViewModel } from '@/workspaces/analytics/api/viewModel'
import type { AnalyticsApiResponse } from '@/workspaces/analytics/api/types'

function jsonResponse(body: unknown) {
  return { status: 200, ok: true, text: async () => JSON.stringify(body) } as Response
}

describe('analyticsApi.getAnalytics', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse({})))
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('requests /v1/analytics/trends with the given dataset and period', async () => {
    await getAnalytics({ datasetId: 'dataset-1', period: 'last-quarter' })

    const [requestedUrl] = vi.mocked(fetch).mock.calls[0]
    const url = new URL(String(requestedUrl))
    expect(url.pathname).toContain('/v1/analytics/trends')
    expect(url.searchParams.get('datasetId')).toBe('dataset-1')
    expect(url.searchParams.get('period')).toBe('last-quarter')
  })

  it('sends only datasetId and period', async () => {
    await getAnalytics({ datasetId: 'dataset-1', period: 'last-30-days' })

    const [requestedUrl] = vi.mocked(fetch).mock.calls[0]
    const url = new URL(String(requestedUrl))
    expect([...url.searchParams.keys()].sort()).toEqual(['datasetId', 'period'])
  })
})

const SAMPLE_RESPONSE: AnalyticsApiResponse = {
  period: 'Last 30 Days',
  volumeTrend: [
    { date: '2026-08-06', count: 10 },
    { date: '2026-08-07', count: 15 },
    { date: '2026-08-08', count: 20 },
  ],
  categoryTrend: [
    { category: 'billing', count: 18 },
    { category: 'shipping', count: 9 },
  ],
  regionTrend: [
    { region: 'EMEA', count: 12 },
    { region: 'unknown', count: 3 },
  ],
  sentimentTrend: [
    { date: '2026-08-07', averageScore: -0.5, labelCounts: { negative: 8, neutral: 2 } },
    { date: '2026-08-08', averageScore: 0.2, labelCounts: { positive: 5, neutral: 3 } },
  ],
  urgencyTrend: [
    { urgency: 'high', count: 7 },
    { urgency: 'low', count: 4 },
  ],
  warnings: [],
}

describe('toAnalyticsViewModel', () => {
  it('builds one TrendNarrative per non-empty real trend array, using only real numbers', () => {
    const viewModel = toAnalyticsViewModel(SAMPLE_RESPONSE)

    expect(viewModel.trends).toHaveLength(5)
    expect(viewModel.trends.map((trend) => trend.id)).toEqual([
      'complaint-volume-trend',
      'category-trend',
      'region-trend',
      'sentiment-trend',
      'urgency-trend',
    ])
  })

  it('volume narrative states the last and first returned days by position only, never a computed total', () => {
    const [volume] = toAnalyticsViewModel(SAMPLE_RESPONSE).trends
    expect(volume.trend).toBe('20 complaint(s) were recorded on 2026-08-08.')
    expect(volume.evidence).toBe('10 complaint(s) were recorded on 2026-08-06.')
  })

  it('category narrative states the returned entries by name and count only, never a ranking claim', () => {
    const categoryNarrative = toAnalyticsViewModel(SAMPLE_RESPONSE).trends.find((trend) => trend.id === 'category-trend')
    expect(categoryNarrative?.trend).toBe('billing recorded 18 complaint(s) in the returned trend data.')
    expect(categoryNarrative?.evidence).toBe('shipping recorded 9 complaint(s) in the returned trend data.')
  })

  it('sentiment narrative states the latest recorded average score verbatim, never an averaged/recomputed value', () => {
    const sentimentNarrative = toAnalyticsViewModel(SAMPLE_RESPONSE).trends.find((trend) => trend.id === 'sentiment-trend')
    expect(sentimentNarrative?.trend).toContain('2026-08-08')
    expect(sentimentNarrative?.trend).toContain('0.2')
    expect(sentimentNarrative?.narrative).toContain('positive: 5')
    expect(sentimentNarrative?.narrative).toContain('neutral: 3')
  })

  it('never uses comparative or ranking language such as "most common," "highest," or "dominant"', () => {
    const viewModel = toAnalyticsViewModel(SAMPLE_RESPONSE)
    const allText = viewModel.trends.map((trend) => `${trend.trend} ${trend.narrative} ${trend.evidence}`).join(' ')
    expect(allText).not.toMatch(
      /\bmost common\b|\bhighest\b|\blowest\b|\bdominant\b|\bsignificant\b|\bconcerning\b|\bindicates\b|\bsuggests\b|\bdriven by\b|\bcorrelated with\b|\btop\b|\bleading\b|\bmajority\b/i,
    )
  })

  it('omits a trend entry entirely for an empty array rather than fabricating one', () => {
    const viewModel = toAnalyticsViewModel({ ...SAMPLE_RESPONSE, regionTrend: [] })
    expect(viewModel.trends.some((trend) => trend.id === 'region-trend')).toBe(false)
    expect(viewModel.trends).toHaveLength(4)
  })

  it('produces no trends at all when every real trend array is empty', () => {
    const viewModel = toAnalyticsViewModel({
      ...SAMPLE_RESPONSE,
      volumeTrend: [],
      categoryTrend: [],
      regionTrend: [],
      sentimentTrend: [],
      urgencyTrend: [],
    })
    expect(viewModel.trends).toEqual([])
  })

  it('never uses evaluative or causal language anywhere in the generated narratives', () => {
    const viewModel = toAnalyticsViewModel(SAMPLE_RESPONSE)
    const allText = viewModel.trends.map((trend) => `${trend.trend} ${trend.narrative} ${trend.evidence}`).join(' ')
    expect(allText).not.toMatch(
      /\bincreased\b|\bdecreased\b|\bimproved\b|\bdeclined\b|\bworsened\b|\bbecause\b|\bimproving\b|\bworsening\b/i,
    )
  })

  it('preserves warnings from the Gateway response unchanged', () => {
    const viewModel = toAnalyticsViewModel({ ...SAMPLE_RESPONSE, warnings: ['x'] })
    expect(viewModel.warnings).toEqual(['x'])
  })
})
