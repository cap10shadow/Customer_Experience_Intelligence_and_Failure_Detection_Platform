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

export interface DescribeApiErrorOptions {
  /**
   * What the user was trying to do, phrased to complete the sentence
   * "... could not <subject>" -- e.g. "record this decision". Keeps the
   * shared wording specific without each caller writing its own full set
   * of status messages.
   */
  subject?: string
}

/**
 * The one shared translation from a transport/HTTP failure into a
 * sentence a user can act on. Previously each surface invented its own
 * subset -- `CopilotPanel` handled `0`/`5xx` and nothing else, the
 * Decision form showed the raw `ApiError.message` for every status, and
 * the workspace `ErrorBoundary` fallbacks showed whatever the Gateway
 * envelope happened to contain. `403` in particular rendered as a bare
 * "Not authorized", which never told the user that their *role* was the
 * reason.
 *
 * Deliberately falls back to the Gateway's own message for anything it
 * doesn't have a better sentence for: the Gateway's error envelope is
 * already written in product terms (`core/errors.py`), so overriding it
 * wholesale would lose real information. Nothing here is ever silently
 * swallowed -- this only chooses the wording of a failure that is always
 * still shown.
 */
export function describeApiError(error: ApiError, { subject }: DescribeApiErrorOptions = {}): string {
  const tail = subject ? ` ${subject}` : ''

  if (error.status === NO_RESPONSE_STATUS) {
    return error.code === 'REQUEST_TIMEOUT'
      ? `The platform took too long to respond, so it could not${tail || ' complete that request'}. Try again.`
      : `The platform could not be reached, so it could not${tail || ' complete that request'}. Check your connection and try again.`
  }
  if (error.status === 401) {
    return 'Your session has ended. Sign in again to continue.'
  }
  if (error.status === 403) {
    return `Your role does not permit this action, so the platform did not${tail || ' complete it'}. An operator or administrator can carry it out.`
  }
  if (error.status === 404) {
    return `That record no longer exists, or the address is out of date.`
  }
  if (error.status === 422 || error.status === 400) {
    return error.message || 'That request was not valid. Check the values entered and try again.'
  }
  if (error.status >= 500) {
    return `The platform is temporarily unavailable, so it could not${tail || ' complete that request'}. Try again shortly.`
  }
  return error.message || 'Something went wrong. Please try again.'
}
