import type { ReactNode } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'

import { DATASET_STORAGE_KEY, DatasetProvider } from '@/app/context/DatasetContext'
import { DashboardContextProvider } from '@/workspaces/dashboard/context'
import { useDashboardData } from '@/workspaces/dashboard/hooks/useDashboardData'
import { ApiError } from '@/app/api/errors'

function jsonResponse(body: unknown, status = 200) {
  return { status, ok: status >= 200 && status < 300, text: async () => JSON.stringify(body) } as Response
}

function wrapper({ children }: { children: ReactNode }) {
  return (
    <DatasetProvider>
      <DashboardContextProvider>{children}</DashboardContextProvider>
    </DatasetProvider>
  )
}

describe('useDashboardData', () => {
  beforeEach(() => {
    window.localStorage.setItem(DATASET_STORAGE_KEY, 'dataset-1')
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    window.localStorage.removeItem(DATASET_STORAGE_KEY)
  })

  it('starts in a loading state with no data or error', () => {
    vi.stubGlobal('fetch', vi.fn(() => new Promise(() => {})))

    const { result } = renderHook(() => useDashboardData(), { wrapper })

    expect(result.current.isLoading).toBe(true)
    expect(result.current.data).toBeNull()
    expect(result.current.error).toBeNull()
  })

  it('resolves to the mapped view model on a successful Gateway response', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        jsonResponse({
          operationalBrief: { level: 'stable', summary: 'No active incidents detected.', healthIndicators: [], criticalSituations: [], keyChanges: [], focusAreas: [] },
          decisionSummary: [],
          investigationEntryPoints: [],
          appliedFilters: { timeRange: 'current', region: null, businessUnit: null, productScope: null, userScope: null },
          warnings: [],
        }),
      ),
    )

    const { result } = renderHook(() => useDashboardData(), { wrapper })

    await waitFor(() => expect(result.current.isLoading).toBe(false))

    expect(result.current.error).toBeNull()
    expect(result.current.data?.operationalStatus).toEqual({ level: 'stable', summary: 'No active incidents detected.' })
  })

  it('resolves to an ApiError when the Gateway returns an error envelope', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        jsonResponse({ error: { code: 'DOWNSTREAM_SERVICE_UNAVAILABLE', message: 'Unavailable.', requestId: 'req-1' } }, 503),
      ),
    )

    const { result } = renderHook(() => useDashboardData(), { wrapper })

    await waitFor(() => expect(result.current.isLoading).toBe(false))

    expect(result.current.data).toBeNull()
    expect(result.current.error).toBeInstanceOf(ApiError)
    expect(result.current.error?.code).toBe('DOWNSTREAM_SERVICE_UNAVAILABLE')
  })
})
