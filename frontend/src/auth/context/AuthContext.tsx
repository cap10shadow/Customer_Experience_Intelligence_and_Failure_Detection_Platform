// This file necessarily exports both `AuthProvider` (a component) and
// `useAuth` (a hook) -- the standard React context co-location idiom,
// the same unavoidable-multi-export situation AppRouter.tsx's own
// `/* eslint-disable react-refresh/only-export-components */` already
// precedents in this repository.
/* eslint-disable react-refresh/only-export-components */
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'

import { ApiError } from '@/app/api/errors'
import { setUnauthorizedListener } from '@/app/api/unauthorized'

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
  /**
   * True only for the specific case of a session that was genuinely
   * established and then stopped being accepted -- an expired or
   * server-invalidated session, never "you have not signed in yet" and
   * never a rejected password. `LoginPage` uses it to explain *why* the
   * user is back at the sign-in form; a deliberate sign-out clears it.
   */
  sessionExpired: boolean
  /** Whether the signed-in user holds `role` (or a role that outranks it) -- mirrors the Gateway's own hierarchy, and is never treated as the authorization boundary. */
  hasRole: (role: PlatformRole) => boolean
  login: (request: LoginRequest) => Promise<void>
  logout: () => Promise<void>
}

/**
 * The three canonical roles seeded by migration `12fef1ff2286` and
 * enforced by `gateway_service/app/core/roles.py`. Listed lowest- to
 * highest-privilege: the Gateway's `require_role` treats a higher role
 * as satisfying a lower one, and `hasRole` below mirrors that exactly so
 * the UI's explanation of a restriction can never contradict what the
 * backend will actually do.
 */
export type PlatformRole = 'viewer' | 'operator' | 'admin'

const ROLE_RANK: Record<PlatformRole, number> = { viewer: 0, operator: 1, admin: 2 }

function isPlatformRole(value: string): value is PlatformRole {
  return value === 'viewer' || value === 'operator' || value === 'admin'
}

const AuthContext = createContext<AuthContextValue | null>(null)

export interface AuthProviderProps {
  children: ReactNode
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [status, setStatus] = useState<AuthStatus>('checking')
  const [user, setUser] = useState<AuthenticatedUser | null>(null)
  const [sessionExpired, setSessionExpired] = useState(false)
  // Read inside the module-level 401 listener, which is registered once
  // and must observe the *current* status without re-registering (and
  // without capturing a stale value) on every status change. Synced in
  // an effect rather than during render -- a ref written during render
  // is a real correctness hazard under concurrent rendering, not just a
  // lint preference.
  const statusRef = useRef<AuthStatus>('checking')
  useEffect(() => {
    statusRef.current = status
  }, [status])

  useEffect(() => {
    // Any 401, from any workspace call, means the Gateway no longer
    // accepts this browser's session (see app/api/unauthorized.ts). If we
    // were previously authenticated, that is an expiry/invalidation worth
    // explaining; otherwise it is just the ordinary signed-out state.
    return setUnauthorizedListener(() => {
      if (statusRef.current === 'authenticated') {
        setSessionExpired(true)
      }
      setUser(null)
      setStatus('unauthenticated')
    })
  }, [])

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
    setSessionExpired(false)
  }, [])

  const logout = useCallback(async () => {
    try {
      await logoutRequest()
    } finally {
      setUser(null)
      setStatus('unauthenticated')
      // A deliberate sign-out is not an expiry -- clear the notice so the
      // login page never tells a user their session "expired" when they
      // signed out on purpose.
      setSessionExpired(false)
    }
  }, [])

  const hasRole = useCallback(
    (role: PlatformRole) => {
      const held = user?.roles ?? []
      return held.some((candidate) => isPlatformRole(candidate) && ROLE_RANK[candidate] >= ROLE_RANK[role])
    },
    [user],
  )

  const value = useMemo<AuthContextValue>(
    () => ({ status, user, sessionExpired, hasRole, login, logout }),
    [status, user, sessionExpired, hasRole, login, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)
  if (context === null) {
    throw new Error('useAuth must be used within an AuthProvider.')
  }
  return context
}

/**
 * The same context, but tolerant of being read outside `AuthProvider`.
 *
 * For anything that *depends* on a session, `useAuth` and its hard error
 * remain correct -- a missing provider there is a real misconfiguration.
 * This variant exists for the narrow case of a component that renders
 * perfectly well without session information and only uses it to *add*
 * an explanation: a workspace section that tells the user their role
 * cannot perform a write. Those components are also rendered in
 * isolation by component-level tests, where there is no session and no
 * meaningful one to fabricate.
 *
 * Reading `null` here means "no session information available," which
 * deliberately renders no role restriction rather than guessing one.
 * That is safe in exactly one direction and only because frontend
 * visibility is never the authorization boundary (§12 of the frozen
 * architecture): the Gateway rejects an unauthorized write regardless of
 * what this returns.
 */
export function useOptionalAuth(): AuthContextValue | null {
  return useContext(AuthContext)
}
