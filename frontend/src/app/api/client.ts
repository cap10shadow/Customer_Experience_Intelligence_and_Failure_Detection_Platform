/**
 * The one centralized HTTP client every workspace API module (Parts 2-5)
 * builds on -- per Batch 1 §7, workspace-specific endpoint semantics
 * (paths, query shapes, response types) stay out of this file; this file
 * owns only: base URL resolution, request construction, JSON handling,
 * timeout/abort, correlation ID, and turning a Gateway error envelope
 * into a typed ApiError. Deliberately built on native fetch rather than
 * a library -- nothing in the frozen architecture requires one, and this
 * repository doesn't have one installed.
 */
import { env } from '@/app/configuration/env'

import { ApiError, NO_RESPONSE_STATUS } from './errors'

const DEFAULT_TIMEOUT_MS = 10_000

export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'

export interface ApiRequestOptions {
  method?: HttpMethod
  query?: Record<string, string | number | boolean | undefined | null>
  body?: unknown
  timeoutMs?: number
  signal?: AbortSignal
}

interface GatewayErrorEnvelope {
  error: {
    code: string
    message: string
    requestId?: string
    details?: unknown
  }
}

function isGatewayErrorEnvelope(value: unknown): value is GatewayErrorEnvelope {
  return (
    typeof value === 'object' &&
    value !== null &&
    'error' in value &&
    typeof (value as { error: unknown }).error === 'object' &&
    (value as { error: unknown }).error !== null
  )
}

function createRequestId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  return `req-${Date.now()}-${Math.random().toString(16).slice(2)}`
}

function buildUrl(path: string, query?: ApiRequestOptions['query']): string {
  const base = env.apiBaseUrl.replace(/\/$/, '')
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  const url = new URL(`${base}${normalizedPath}`, window.location.origin)

  if (query) {
    for (const [key, value] of Object.entries(query)) {
      if (value !== undefined && value !== null) {
        url.searchParams.set(key, String(value))
      }
    }
  }

  return url.toString()
}

function safeJsonParse(text: string): unknown {
  try {
    return JSON.parse(text)
  } catch {
    return null
  }
}

/**
 * Issues one HTTP request against the Gateway and resolves to the parsed
 * JSON body, or rejects with an ApiError for every failure mode: a
 * Gateway error envelope, a non-JSON/unexpected error response, a network
 * failure, or a client-side timeout.
 */
export async function apiRequest<TResponse>(path: string, options: ApiRequestOptions = {}): Promise<TResponse> {
  const { method = 'GET', query, body, timeoutMs = DEFAULT_TIMEOUT_MS, signal } = options

  const requestId = createRequestId()
  const url = buildUrl(path, query)

  const controller = new AbortController()
  const timeoutHandle = setTimeout(() => controller.abort(), timeoutMs)
  const externalAbortListener = () => controller.abort()
  signal?.addEventListener('abort', externalAbortListener, { once: true })

  let response: Response
  try {
    response = await fetch(url, {
      method,
      headers: {
        Accept: 'application/json',
        ...(body !== undefined ? { 'Content-Type': 'application/json' } : {}),
        'X-Request-ID': requestId,
      },
      body: body !== undefined ? JSON.stringify(body) : undefined,
      signal: controller.signal,
      // Phase 13 Batch 2 (AD-6): the Gateway's session is an HttpOnly
      // cookie, never read by this client -- the browser attaches it
      // automatically, but only if the request explicitly opts in.
      // Same-origin (see docker-compose.yml/vite.config.ts's proxy) as
      // of this batch, so 'same-origin' would suffice; 'include' is used
      // instead so this doesn't silently stop working if a future,
      // still-same-origin deployment topology (§20 of the frozen
      // architecture) ever routes this through an intermediate redirect.
      credentials: 'include',
    })
  } catch (cause) {
    if (controller.signal.aborted) {
      throw new ApiError({
        code: 'REQUEST_TIMEOUT',
        message: 'The request timed out.',
        status: NO_RESPONSE_STATUS,
        requestId,
      })
    }
    throw new ApiError({
      code: 'NETWORK_ERROR',
      message: 'The request could not be completed.',
      status: NO_RESPONSE_STATUS,
      requestId,
      details: cause instanceof Error ? cause.message : undefined,
    })
  } finally {
    clearTimeout(timeoutHandle)
    signal?.removeEventListener('abort', externalAbortListener)
  }

  if (response.status === 204) {
    return undefined as TResponse
  }

  const rawText = await response.text()
  const payload = rawText ? safeJsonParse(rawText) : null

  if (!response.ok) {
    const envelope = isGatewayErrorEnvelope(payload) ? payload.error : null

    throw new ApiError({
      code: envelope?.code ?? 'UNKNOWN_ERROR',
      message: envelope?.message ?? `Request failed with status ${response.status}.`,
      status: response.status,
      requestId: envelope?.requestId ?? requestId,
      details: envelope?.details,
    })
  }

  return payload as TResponse
}

export const apiClient = {
  get: <TResponse>(path: string, options?: Omit<ApiRequestOptions, 'method' | 'body'>) =>
    apiRequest<TResponse>(path, { ...options, method: 'GET' }),
  post: <TResponse>(path: string, body?: unknown, options?: Omit<ApiRequestOptions, 'method' | 'body'>) =>
    apiRequest<TResponse>(path, { ...options, method: 'POST', body }),
  put: <TResponse>(path: string, body?: unknown, options?: Omit<ApiRequestOptions, 'method' | 'body'>) =>
    apiRequest<TResponse>(path, { ...options, method: 'PUT', body }),
  patch: <TResponse>(path: string, body?: unknown, options?: Omit<ApiRequestOptions, 'method' | 'body'>) =>
    apiRequest<TResponse>(path, { ...options, method: 'PATCH', body }),
  delete: <TResponse>(path: string, options?: Omit<ApiRequestOptions, 'method' | 'body'>) =>
    apiRequest<TResponse>(path, { ...options, method: 'DELETE' }),
}
