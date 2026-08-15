import { afterEach, describe, expect, it, vi } from 'vitest'
import { act, renderHook, waitFor } from '@testing-library/react'

import { AuthProvider, useAuth } from '@/auth/context/AuthContext'

function jsonResponse(body: unknown, status = 200) {
  return { status, ok: status >= 200 && status < 300, text: async () => JSON.stringify(body) } as Response
}

const SAMPLE_USER = { userId: 'user-1', email: 'alice@example.com', roles: ['viewer'] }

describe('AuthContext', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('starts in "checking" and transitions to "authenticated" when GET /auth/me succeeds', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(SAMPLE_USER)))

    const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider })

    expect(result.current.status).toBe('checking')

    await waitFor(() => expect(result.current.status).toBe('authenticated'))
    expect(result.current.user).toEqual(SAMPLE_USER)
  })

  it('transitions to "unauthenticated" when GET /auth/me returns 401', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        jsonResponse({ error: { code: 'UNAUTHENTICATED', message: 'Authentication required.', requestId: 'req-1' } }, 401),
      ),
    )

    const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider })

    await waitFor(() => expect(result.current.status).toBe('unauthenticated'))
    expect(result.current.user).toBeNull()
  })

  it('transitions to "error" (not "unauthenticated") on a non-401 bootstrap failure', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('network down')))

    const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider })

    await waitFor(() => expect(result.current.status).toBe('error'))
  })

  it('login() sets the authenticated user and status', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValueOnce(jsonResponse({ error: { code: 'UNAUTHENTICATED', message: 'x', requestId: 'r' } }, 401)),
    )

    const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider })
    await waitFor(() => expect(result.current.status).toBe('unauthenticated'))

    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(SAMPLE_USER)))
    await act(async () => {
      await result.current.login({ email: 'alice@example.com', password: 'correct-password' })
    })

    expect(result.current.status).toBe('authenticated')
    expect(result.current.user).toEqual(SAMPLE_USER)
  })

  it('logout() clears the user and sets status to "unauthenticated"', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(SAMPLE_USER)))
    const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider })
    await waitFor(() => expect(result.current.status).toBe('authenticated'))

    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ status: 204, ok: true, text: async () => '' } as Response))
    await act(async () => {
      await result.current.logout()
    })

    expect(result.current.status).toBe('unauthenticated')
    expect(result.current.user).toBeNull()
  })

  it('useAuth throws when used outside an AuthProvider', () => {
    expect(() => renderHook(() => useAuth())).toThrow('useAuth must be used within an AuthProvider.')
  })
})
