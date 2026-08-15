// This file necessarily exports both `AuthProvider` (a component) and
// `useAuth` (a hook) -- the standard React context co-location idiom,
// the same unavoidable-multi-export situation AppRouter.tsx's own
// `/* eslint-disable react-refresh/only-export-components */` already
// precedents in this repository.
/* eslint-disable react-refresh/only-export-components */
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'

import { ApiError } from '@/app/api/errors'

import { fetchCurrentUser, login as loginRequest, logout as logoutRequest } from '../api/authApi'
import type { AuthenticatedUser, LoginRequest } from '../api/types'

/**
 * Represents "the server says this browser is authenticated" -- never
 * the credential itself (Phase 13 Batch 2, §11 of the frozen
 * architecture's Frontend Integration section). No JWT/session value is
 * ever held in this state; the HttpOnly cookie is the only place the
 * credential lives, and this context never reads it.
 *
 * - `checking`: session bootstrap (GET /auth/me) is in flight.
 * - `authenticated`: a real session was confirmed by the Gateway.
 * - `unauthenticated`: no valid session (never logged in, or a 401).
 * - `error`: the bootstrap call itself failed for a reason other than
 *   401 (network/5xx) -- kept distinct from `unauthenticated` so a
 *   transient failure doesn't look identical to "you're logged out."
 */
export type AuthStatus = 'checking' | 'authenticated' | 'unauthenticated' | 'error'

export interface AuthContextValue {
  status: AuthStatus
  user: AuthenticatedUser | null
  login: (request: LoginRequest) => Promise<void>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export interface AuthProviderProps {
  children: ReactNode
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [status, setStatus] = useState<AuthStatus>('checking')
  const [user, setUser] = useState<AuthenticatedUser | null>(null)

  useEffect(() => {
    let cancelled = false

    fetchCurrentUser()
      .then((currentUser) => {
        if (cancelled) return
        setUser(currentUser)
        setStatus('authenticated')
      })
      .catch((error: unknown) => {
        if (cancelled) return
        if (error instanceof ApiError && error.status === 401) {
          setStatus('unauthenticated')
        } else {
          setStatus('error')
        }
      })

    return () => {
      cancelled = true
    }
  }, [])

  const login = useCallback(async (request: LoginRequest) => {
    const authenticatedUser = await loginRequest(request)
    setUser(authenticatedUser)
    setStatus('authenticated')
  }, [])

  const logout = useCallback(async () => {
    try {
      await logoutRequest()
    } finally {
      setUser(null)
      setStatus('unauthenticated')
    }
  }, [])

  const value = useMemo<AuthContextValue>(() => ({ status, user, login, logout }), [status, user, login, logout])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)
  if (context === null) {
    throw new Error('useAuth must be used within an AuthProvider.')
  }
  return context
}
