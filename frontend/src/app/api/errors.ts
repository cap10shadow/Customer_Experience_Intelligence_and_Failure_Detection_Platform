/**
 * Mirrors the Gateway's standardized error envelope
 * (backend/services/gateway_service/app/core/errors.py's ErrorEnvelope) so
 * a caught ApiError always carries the same shape regardless of whether
 * the failure came from the Gateway itself, a network failure the browser
 * raised before any response existed, or a client-side timeout/abort.
 */
export interface ApiErrorParams {
  code: string
  message: string
  status: number
  requestId?: string
  details?: unknown
}

export class ApiError extends Error {
  readonly code: string
  readonly status: number
  readonly requestId?: string
  readonly details?: unknown

  constructor({ code, message, status, requestId, details }: ApiErrorParams) {
    super(message)
    this.name = 'ApiError'
    this.code = code
    this.status = status
    this.requestId = requestId
    this.details = details
  }
}

/** Client-side failures with no HTTP response at all get status 0. */
export const NO_RESPONSE_STATUS = 0
