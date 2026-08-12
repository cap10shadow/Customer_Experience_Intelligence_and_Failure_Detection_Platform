import { afterEach, describe, expect, it, vi } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'

import { useRecommendationData } from '@/workspaces/recommendations/hooks/useRecommendationData'
import { ApiError } from '@/app/api/errors'

function jsonResponse(body: unknown, status = 200) {
  return { status, ok: status >= 200 && status < 300, text: async () => JSON.stringify(body) } as Response
}

describe('useRecommendationData', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('does not fetch and resolves immediately when there is no recommendationId', () => {
    vi.stubGlobal('fetch', vi.fn())

    const { result } = renderHook(() => useRecommendationData(null))

    expect(result.current.data).toBeNull()
    expect(result.current.isLoading).toBe(false)
    expect(result.current.error).toBeNull()
    expect(typeof result.current.refetch).toBe('function')
    expect(fetch).not.toHaveBeenCalled()
  })

  it('starts loading and fetches when a recommendationId is present', () => {
    vi.stubGlobal('fetch', vi.fn(() => new Promise(() => {})))

    const { result } = renderHook(() => useRecommendationData('rec-1'))

    expect(result.current.isLoading).toBe(true)
    expect(fetch).toHaveBeenCalled()
  })

  it('resolves to the mapped view model on a successful Gateway response', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        jsonResponse({
          recommendationId: 'rec-1',
          incidentId: 'incident-1',
          generationId: 'gen-1',
          category: 'escalate',
          priority: 'high',
          score: 88,
          action: 'Escalate to payments team',
          recommendationRationale: 'r',
          priorityRationale: 'p',
          supportingEvidence: [],
          createdAt: '2026-08-08T01:05:00Z',
          decision: null,
          decisionNote: null,
          decidedAt: null,
        }),
      ),
    )

    const { result } = renderHook(() => useRecommendationData('rec-1'))

    await waitFor(() => expect(result.current.isLoading).toBe(false))

    expect(result.current.error).toBeNull()
    expect(result.current.data?.recommendationId).toBe('rec-1')
    expect(result.current.data?.incidentId).toBe('incident-1')
    expect(result.current.data?.overview.headline).toBe('Escalate to payments team')
  })

  it('resolves to an ApiError when the Gateway returns a 404', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(jsonResponse({ error: { code: 'RESOURCE_NOT_FOUND', message: 'Not found.', requestId: 'req-1' } }, 404)),
    )

    const { result } = renderHook(() => useRecommendationData('missing-recommendation'))

    await waitFor(() => expect(result.current.isLoading).toBe(false))

    expect(result.current.data).toBeNull()
    expect(result.current.error).toBeInstanceOf(ApiError)
    expect(result.current.error?.code).toBe('RESOURCE_NOT_FOUND')
  })

  it('re-fetches when recommendationId changes', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({
        recommendationId: 'rec-2',
        incidentId: 'incident-2',
        generationId: 'gen-2',
        category: 'monitor',
        priority: 'low',
        score: 10,
        action: 'Continue monitoring',
        recommendationRationale: 'r',
        priorityRationale: 'p',
        supportingEvidence: [],
        createdAt: '2026-08-08T01:05:00Z',
      }),
    )
    vi.stubGlobal('fetch', fetchMock)

    const { result, rerender } = renderHook(({ id }) => useRecommendationData(id), { initialProps: { id: 'rec-1' } })
    await waitFor(() => expect(result.current.isLoading).toBe(false))

    rerender({ id: 'rec-2' })
    await waitFor(() => expect(result.current.data?.recommendationId).toBe('rec-2'))

    expect(fetchMock).toHaveBeenCalledTimes(2)
    const [firstUrl] = fetchMock.mock.calls[0]
    const [secondUrl] = fetchMock.mock.calls[1]
    expect(String(firstUrl)).toContain('/recommendations/rec-1')
    expect(String(secondUrl)).toContain('/recommendations/rec-2')
  })
})
