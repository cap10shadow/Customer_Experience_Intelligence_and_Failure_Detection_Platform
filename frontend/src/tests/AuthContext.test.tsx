import { afterEach, describe, expect, it, vi } from 'vitest'
import { act, renderHook, waitFor } from '@testing-library/react'

import { apiClient } from '@/app/api/client'
import { AuthProvider, useAuth, useOptionalAuth } from '@/auth/context/AuthContext'

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

  it('useOptionalAuth returns null outside an AuthProvider instead of throwing', () => {
    const { result } = renderHook(() => useOptionalAuth())
    expect(result.current).toBeNull()
  })

  /**
   * The session-expiry path. Before the centralized 401 signal existed,
   * `AuthContext` only ever learned about authentication once, at
   * bootstrap: a session that expired mid-use produced a 401 on every
   * workspace fetch, each workspace showed a generic "something went
   * wrong", and the user was never returned to the login screen.
   */
  it('signs the user out and flags an expiry when any later request returns 401', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(SAMPLE_USER)))
    const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider })
    await waitFor(() => expect(result.current.status).toBe('authenticated'))
    expect(result.current.sessionExpired).toBe(false)

    // A workspace fetch, long after bootstrap, whose session has lapsed.
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        jsonResponse({ error: { code: 'UNAUTHENTICATED', message: 'Authentication required.', requestId: 'r' } }, 401),
      ),
    )
    await act(async () => {
      await apiClient.get('/v1/dashboard').catch(() => undefined)
    })

    expect(result.current.status).toBe('unauthenticated')
    expect(result.current.user).toBeNull()
    expect(result.current.sessionExpired).toBe(true)
  })

  it('does not flag an expiry for a 401 when there was never a session to expire', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        jsonResponse({ error: { code: 'UNAUTHENTICATED', message: 'Authentication required.', requestId: 'r' } }, 401),
      ),
    )

    const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider })
    await waitFor(() => expect(result.current.status).toBe('unauthenticated'))
    expect(result.current.sessionExpired).toBe(false)
  })

  it('clears the expiry flag on a deliberate sign-out, so the login page never mislabels it', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(SAMPLE_USER)))
    const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider })
    await waitFor(() => expect(result.current.status).toBe('authenticated'))

    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        jsonResponse({ error: { code: 'UNAUTHENTICATED', message: 'Authentication required.', requestId: 'r' } }, 401),
      ),
    )
    await act(async () => {
      await apiClient.get('/v1/dashboard').catch(() => undefined)
    })
    expect(result.current.sessionExpired).toBe(true)

    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ status: 204, ok: true, text: async () => '' } as Response))
    await act(async () => {
      await result.current.logout()
    })
    expect(result.current.sessionExpired).toBe(false)
  })

  describe('hasRole mirrors the Gateway role hierarchy', () => {
    async function renderWithRoles(roles: string[]) {
      vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse({ ...SAMPLE_USER, roles })))
      const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider })
      await waitFor(() => expect(result.current.status).toBe('authenticated'))
      return result
    }

    it('treats a higher role as satisfying a lower one, exactly as require_role does', async () => {
      const result = await renderWithRoles(['admin'])
      expect(result.current.hasRole('viewer')).toBe(true)
      expect(result.current.hasRole('operator')).toBe(true)
      expect(result.current.hasRole('admin')).toBe(true)
    })

    it('does not treat a lower role as satisfying a higher one', async () => {
      const result = await renderWithRoles(['viewer'])
      expect(result.current.hasRole('viewer')).toBe(true)
      expect(result.current.hasRole('operator')).toBe(false)
    })

    it('grants nothing to a session with no roles assigned', async () => {
      const result = await renderWithRoles([])
      expect(result.current.hasRole('viewer')).toBe(false)
      expect(result.current.hasRole('operator')).toBe(false)
    })

    it('ignores an unrecognized role name rather than guessing its rank', async () => {
      const result = await renderWithRoles(['superuser'])
      expect(result.current.hasRole('viewer')).toBe(false)
    })
  })
})
