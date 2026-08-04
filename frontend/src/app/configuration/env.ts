/**
 * Typed access to build-time environment variables. No API calls are made
 * from this phase's architecture (Step 1 explicitly excludes backend
 * integration) -- this exists so the one env var the platform already
 * defines (`docker-compose.yml`'s `VITE_API_BASE_URL`) has a single,
 * typed read path ready for the first workspace that needs it, instead
 * of scattered `import.meta.env.VITE_*` accesses.
 */
export const env = {
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL ?? '/api',
} as const
