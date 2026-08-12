import type { ReactNode } from 'react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'

import { InvestigationContextProvider } from '@/workspaces/investigations/context'
import { useInvestigationData } from '@/workspaces/investigations/hooks/useInvestigationData'
import { ApiError } from '@/app/api/errors'

function jsonResponse(body: unknown, status = 200) {
  return { status, ok: status >= 200 && status < 300, text: async () => JSON.stringify(body) } as Response
}

function wrapperFor(incidentId: string | null) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return <InvestigationContextProvider incidentId={incidentId}>{children}</InvestigationContextProvider>
  }
}

describe('useInvestigationData', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('does not fetch and resolves immediately when there is no incidentId', () => {
    vi.stubGlobal('fetch', vi.fn())

    const { result } = renderHook(() => useInvestigationData(), { wrapper: wrapperFor(null) })

    expect(result.current.data).toBeNull()
    expect(result.current.isLoading).toBe(false)
    expect(result.current.error).toBeNull()
    expect(typeof result.current.refetch).toBe('function')
    expect(fetch).not.toHaveBeenCalled()
  })

  it('starts loading and fetches when an incidentId is present', () => {
    vi.stubGlobal('fetch', vi.fn(() => new Promise(() => {})))

    const { result } = renderHook(() => useInvestigationData(), { wrapper: wrapperFor('incident-1') })

    expect(result.current.isLoading).toBe(true)
    expect(fetch).toHaveBeenCalled()
  })

  it('resolves to the mapped view model on a successful Gateway response', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        jsonResponse({
          incidentId: 'incident-1',
          observation: { headline: 'h', description: 'd' },
          evidence: [],
          rootCause: null,
          businessImpact: [],
          businessImpactConfidenceLevel: null,
          recommendedNextStep: null,
          warnings: [],
        }),
      ),
    )

    const { result } = renderHook(() => useInvestigationData(), { wrapper: wrapperFor('incident-1') })

    await waitFor(() => expect(result.current.isLoading).toBe(false))

    expect(result.current.error).toBeNull()
    expect(result.current.data?.observation).toEqual({ headline: 'h', description: 'd' })
  })

  it('resolves to an ApiError when the Gateway returns a 404', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(jsonResponse({ error: { code: 'RESOURCE_NOT_FOUND', message: 'Not found.', requestId: 'req-1' } }, 404)),
    )

    const { result } = renderHook(() => useInvestigationData(), { wrapper: wrapperFor('missing-incident') })

    await waitFor(() => expect(result.current.isLoading).toBe(false))

    expect(result.current.data).toBeNull()
    expect(result.current.error).toBeInstanceOf(ApiError)
    expect(result.current.error?.code).toBe('RESOURCE_NOT_FOUND')
  })
})
