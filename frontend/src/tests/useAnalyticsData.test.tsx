import type { ReactNode } from 'react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'

import { AnalyticsContextProvider } from '@/workspaces/analytics/context'
import { useAnalyticsData } from '@/workspaces/analytics/hooks/useAnalyticsData'
import { ApiError } from '@/app/api/errors'

function jsonResponse(body: unknown, status = 200) {
  return { status, ok: status >= 200 && status < 300, text: async () => JSON.stringify(body) } as Response
}

function wrapper({ children }: { children: ReactNode }) {
  return <AnalyticsContextProvider>{children}</AnalyticsContextProvider>
}

const SAMPLE_RESPONSE = {
  period: 'Last 30 Days',
  volumeTrend: [{ date: '2026-08-08', count: 20 }],
  categoryTrend: [],
  regionTrend: [],
  sentimentTrend: [],
  urgencyTrend: [],
  warnings: [],
}

describe('useAnalyticsData', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('starts in a loading state with no data or error', () => {
    vi.stubGlobal('fetch', vi.fn(() => new Promise(() => {})))

    const { result } = renderHook(() => useAnalyticsData(), { wrapper })

    expect(result.current.isLoading).toBe(true)
    expect(result.current.data).toBeNull()
    expect(result.current.error).toBeNull()
  })

  it('requests the default "last 30 days" period on first mount', () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(SAMPLE_RESPONSE))
    vi.stubGlobal('fetch', fetchMock)

    renderHook(() => useAnalyticsData(), { wrapper })

    const [requestedUrl] = fetchMock.mock.calls[0]
    const url = new URL(String(requestedUrl))
    expect(url.searchParams.get('period')).toBe('last-30-days')
  })

  it('resolves to the mapped view model on a successful Gateway response', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(SAMPLE_RESPONSE)))

    const { result } = renderHook(() => useAnalyticsData(), { wrapper })

    await waitFor(() => expect(result.current.isLoading).toBe(false))

    expect(result.current.error).toBeNull()
    expect(result.current.data?.trends).toHaveLength(1)
    expect(result.current.data?.trends[0].id).toBe('complaint-volume-trend')
  })

  it('resolves to an ApiError when the Gateway returns an error envelope', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        jsonResponse({ error: { code: 'DOWNSTREAM_SERVICE_FAILURE', message: 'Failed.', requestId: 'req-1' } }, 502),
      ),
    )

    const { result } = renderHook(() => useAnalyticsData(), { wrapper })

    await waitFor(() => expect(result.current.isLoading).toBe(false))

    expect(result.current.data).toBeNull()
    expect(result.current.error).toBeInstanceOf(ApiError)
    expect(result.current.error?.code).toBe('DOWNSTREAM_SERVICE_FAILURE')
  })
})
