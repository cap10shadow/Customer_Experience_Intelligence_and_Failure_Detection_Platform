import { afterEach, describe, expect, it, vi } from 'vitest'

import { fetchCurrentUser, login, logout } from '@/auth/api/authApi'

function jsonResponse(body: unknown, status = 200) {
  return { status, ok: status >= 200 && status < 300, text: async () => JSON.stringify(body) } as Response
}

const SAMPLE_USER = { userId: 'user-1', email: 'alice@example.com', roles: ['viewer'] }

describe('authApi', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('login() posts to the relative /v1/auth/login path and includes credentials', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(SAMPLE_USER)))

    const result = await login({ email: 'alice@example.com', password: 'correct-password' })

    expect(result).toEqual(SAMPLE_USER)
    const [requestedUrl, init] = vi.mocked(fetch).mock.calls[0]
    const url = new URL(String(requestedUrl))
    expect(url.pathname).toContain('/v1/auth/login')
    expect((init as RequestInit).method).toBe('POST')
    expect((init as RequestInit).credentials).toBe('include')
  })

  it('fetchCurrentUser() gets /v1/auth/me', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(SAMPLE_USER)))

    const result = await fetchCurrentUser()

    expect(result).toEqual(SAMPLE_USER)
    const [requestedUrl] = vi.mocked(fetch).mock.calls[0]
    expect(new URL(String(requestedUrl)).pathname).toContain('/v1/auth/me')
  })

  it('logout() posts to /v1/auth/logout', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ status: 204, ok: true, text: async () => '' } as Response))

    await logout()

    const [requestedUrl, init] = vi.mocked(fetch).mock.calls[0]
    expect(new URL(String(requestedUrl)).pathname).toContain('/v1/auth/logout')
    expect((init as RequestInit).method).toBe('POST')
  })
})
