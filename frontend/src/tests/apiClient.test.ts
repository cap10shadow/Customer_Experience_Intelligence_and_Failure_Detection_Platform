import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { apiClient, apiRequest } from '@/app/api/client'
import { ApiError } from '@/app/api/errors'

function jsonResponse(body: unknown, init: { status?: number; ok?: boolean } = {}) {
  const status = init.status ?? 200
  return {
    status,
    ok: init.ok ?? (status >= 200 && status < 300),
    text: async () => JSON.stringify(body),
  } as Response
}

function emptyResponse(status: number) {
  return {
    status,
    ok: status >= 200 && status < 300,
    text: async () => '',
  } as Response
}

describe('apiClient', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn())
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('resolves with the parsed JSON body on success', async () => {
    vi.mocked(fetch).mockResolvedValueOnce(jsonResponse({ id: 'incident-1' }))

    const result = await apiClient.get<{ id: string }>('/dashboard')

    expect(result).toEqual({ id: 'incident-1' })
  })

  it('requests the configured base URL joined with the given path', async () => {
    vi.mocked(fetch).mockResolvedValueOnce(jsonResponse({}))

    await apiClient.get('/dashboard')

    const [requestedUrl] = vi.mocked(fetch).mock.calls[0]
    expect(String(requestedUrl)).toContain('/api/dashboard')
  })

  it('sends a generated X-Request-ID header on every request', async () => {
    vi.mocked(fetch).mockResolvedValueOnce(jsonResponse({}))

    await apiClient.get('/dashboard')

    const [, init] = vi.mocked(fetch).mock.calls[0]
    const headers = init?.headers as Record<string, string>
    expect(headers['X-Request-ID']).toBeTruthy()
  })

  it('serializes the body and sets Content-Type for POST requests', async () => {
    vi.mocked(fetch).mockResolvedValueOnce(jsonResponse({ accepted: true }))

    await apiClient.post('/recommendations/rec-1/notes', { note: 'looks good' })

    const [, init] = vi.mocked(fetch).mock.calls[0]
    expect(init?.method).toBe('POST')
    expect(init?.body).toBe(JSON.stringify({ note: 'looks good' }))
    const headers = init?.headers as Record<string, string>
    expect(headers['Content-Type']).toBe('application/json')
  })

  it('returns undefined for a 204 No Content response', async () => {
    vi.mocked(fetch).mockResolvedValueOnce(emptyResponse(204))

    const result = await apiClient.delete('/investigations/incident-1')

    expect(result).toBeUndefined()
  })

  it('rejects with an ApiError built from the Gateway error envelope', async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      jsonResponse(
        {
          error: {
            code: 'RESOURCE_NOT_FOUND',
            message: 'Incident was not found.',
            requestId: 'gateway-request-id',
            details: { incidentId: 'abc-123' },
          },
        },
        { status: 404, ok: false },
      ),
    )

    await expect(apiClient.get('/investigations/abc-123')).rejects.toMatchObject({
      name: 'ApiError',
      code: 'RESOURCE_NOT_FOUND',
      message: 'Incident was not found.',
      status: 404,
      requestId: 'gateway-request-id',
      details: { incidentId: 'abc-123' },
    })
  })

  it('falls back to a generic ApiError when the error body is not a Gateway envelope', async () => {
    vi.mocked(fetch).mockResolvedValueOnce(emptyResponse(500))

    let caught: unknown
    try {
      await apiClient.get('/dashboard')
    } catch (error) {
      caught = error
    }

    expect(caught).toBeInstanceOf(ApiError)
    expect((caught as ApiError).code).toBe('UNKNOWN_ERROR')
    expect((caught as ApiError).status).toBe(500)
  })

  it('rejects with a NETWORK_ERROR ApiError when fetch itself throws', async () => {
    vi.mocked(fetch).mockRejectedValueOnce(new TypeError('Failed to fetch'))

    await expect(apiClient.get('/dashboard')).rejects.toMatchObject({
      name: 'ApiError',
      code: 'NETWORK_ERROR',
      status: 0,
    })
  })

  it('rejects with a REQUEST_TIMEOUT ApiError when the request exceeds timeoutMs', async () => {
    vi.mocked(fetch).mockImplementation(
      (_url, init) =>
        new Promise((_resolve, reject) => {
          const signal = (init as RequestInit).signal
          signal?.addEventListener('abort', () => {
            const abortError = new Error('This operation was aborted')
            abortError.name = 'AbortError'
            reject(abortError)
          })
        }),
    )

    await expect(apiRequest('/analytics', { timeoutMs: 5 })).rejects.toMatchObject({
      name: 'ApiError',
      code: 'REQUEST_TIMEOUT',
      status: 0,
    })
  })
})
