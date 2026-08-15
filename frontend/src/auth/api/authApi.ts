import { apiClient } from '@/app/api/client'

import type { AuthenticatedUser, LoginRequest } from './types'

/**
 * The Gateway's authentication API (Phase 13 Batch 2, AD-6 §10) --
 * exactly the three routes the frozen architecture names. Paths are
 * relative (`env.apiBaseUrl` supplies the `/api` prefix, proxied to
 * `gateway_service:8000` by `vite.config.ts`), matching the corrected,
 * same-origin convention (see `copilotApi.ts`'s updated comment for the
 * full history). This module never reads or writes the session cookie
 * itself -- the browser handles it automatically once `apiClient`
 * requests with `credentials: 'include'`.
 */

export function login(request: LoginRequest): Promise<AuthenticatedUser> {
  return apiClient.post<AuthenticatedUser>('/v1/auth/login', request)
}

export function logout(): Promise<void> {
  return apiClient.post<void>('/v1/auth/logout')
}

export function fetchCurrentUser(): Promise<AuthenticatedUser> {
  return apiClient.get<AuthenticatedUser>('/v1/auth/me')
}
