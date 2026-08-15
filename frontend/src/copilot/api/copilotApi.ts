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
 * Path history: this originally requested the full `/api/v1/copilot/
 * messages` path (rather than the bare `/copilot/messages` other
 * workspace API modules use, e.g. `recommendationApi.ts`'s
 * `/recommendations/...`) because `docker-compose.yml` set
 * `VITE_API_BASE_URL` to the Gateway's absolute cross-origin URL
 * (`http://localhost:8000`), against which only the fully-prefixed path
 * resolved correctly.
 *
 * Phase 13 Batch 2 (AD-6) removed that override so the frontend and
 * Gateway are same-origin (a same-origin session cookie requires it) --
 * `env.apiBaseUrl` now defaults to `/api` (`frontend/src/app/
 * configuration/env.ts`), routed through `vite.config.ts`'s existing
 * `/api` -> `gateway_service:8000` proxy, which forwards the full
 * request path unchanged. Requesting the fully-prefixed path again here
 * would now double up (`/api` + `/api/v1/...`), so the path below drops
 * the now-redundant leading `/api` -- `apiClient` supplies it from
 * `env.apiBaseUrl`, exactly like every other (already-correct) workspace
 * API module. The repo-wide bare-path-vs-`/api/v1`-prefix mismatch this
 * module used to work around no longer exists for this module; other
 * workspace API modules were not touched (out of this batch's scope).
 */
export function postCopilotMessage(
  request: CopilotQueryRequest,
  options: PostCopilotMessageOptions = {},
): Promise<CopilotResponse> {
  return apiClient.post<CopilotResponse>('/v1/copilot/messages', request, { signal: options.signal })
}
