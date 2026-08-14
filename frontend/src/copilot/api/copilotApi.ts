import { apiClient } from '@/app/api/client'

import type { CopilotQueryRequest, CopilotResponse } from './types'

export interface PostCopilotMessageOptions {
  signal?: AbortSignal
}

/**
 * The Copilot panel's one API call -- through the same centralized
 * `apiClient`/Gateway boundary every workspace uses, never a direct call
 * to `copilot_service` or any downstream domain service.
 *
 * Deliberately requests the full `/api/v1/copilot/messages` path rather
 * than the bare `/copilot/messages` other workspace API modules use
 * (e.g. `recommendationApi.ts`'s `/recommendations/...`): verified against
 * the real running Gateway (`docker compose up gateway_service`) that the
 * bare-path convention 404s (Gateway mounts every router under `/api/v1`
 * -- `gateway_service/app/main.py`), while the prefixed path correctly
 * reaches the mounted route. This is a pre-existing, repo-wide issue
 * affecting every existing workspace API module, not something
 * introduced here -- out of Batch 5's scope to fix repo-wide (see the
 * Batch 5 implementation report). Only this module is written against
 * the path that actually works.
 */
export function postCopilotMessage(
  request: CopilotQueryRequest,
  options: PostCopilotMessageOptions = {},
): Promise<CopilotResponse> {
  return apiClient.post<CopilotResponse>('/api/v1/copilot/messages', request, { signal: options.signal })
}
