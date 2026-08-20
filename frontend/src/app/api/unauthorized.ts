/**
 * The one place a `401` from *any* Gateway call is turned into an
 * application-wide "this browser no longer has a session" signal.
 *
 * Before this existed, `AuthContext` learned about authentication state
 * exactly once -- at bootstrap, via `GET /auth/me`. The Gateway session
 * cookie has a finite `Max-Age` (1800s in the development configuration),
 * so a session that expired *while* the application was open produced a
 * `401` on every subsequent workspace fetch, which each workspace then
 * surfaced through its own `ErrorBoundary` as a generic "Something went
 * wrong loading ..." message. The user was never told their session had
 * ended and was never returned to `/login`; the only recovery was a
 * manual reload. That was one root cause with five identical symptoms
 * (Dashboard, Investigations, Recommendations, Analytics, Administration),
 * so it is fixed once, here, rather than five times in five hooks.
 *
 * Deliberately a tiny module-level registry rather than a React context:
 * `client.ts` is intentionally framework-free (see its own header) and
 * must not import from the auth tree, which would create a cycle
 * (`AuthContext` -> `authApi` -> `client`). The auth provider registers
 * itself here on mount; the client only ever *emits*.
 */

export type UnauthorizedListener = () => void

let listener: UnauthorizedListener | null = null

/**
 * Registers the single application-wide handler for "the Gateway
 * rejected this request with 401". Returns an unsubscribe function so a
 * provider can clean up on unmount (and so tests never leak a handler
 * between cases).
 */
export function setUnauthorizedListener(next: UnauthorizedListener): () => void {
  listener = next
  return () => {
    if (listener === next) {
      listener = null
    }
  }
}

/** Called by the API client for every `401` response. No-op when nothing is registered. */
export function notifyUnauthorized(): void {
  listener?.()
}
