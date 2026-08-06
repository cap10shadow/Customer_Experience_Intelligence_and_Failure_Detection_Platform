import { Skeleton } from '@/shared/components/feedback'
import { Stack } from '@/shared/components/layout'

export interface InvestigationLoadingStateProps {
  /** Announced to screen readers (e.g. "Loading evidence"). */
  label: string
}

/**
 * Skeleton-first loading, matching the treatment the Dashboard
 * established in Phase 10 Step 2 (a spinner communicates "wait"; a
 * skeleton also previews shape, so layout never shifts once real
 * content arrives). Deliberately a local component, not imported from
 * `workspaces/dashboard`, to keep workspaces independent of one
 * another's internals -- the shared `Skeleton` primitive it's built
 * from is the actual reused architecture. Promoting this exact pattern
 * to `shared/` is a reasonable future cleanup once a third workspace
 * needs it, not before.
 */
export function InvestigationLoadingState({ label }: InvestigationLoadingStateProps) {
  return (
    <div aria-busy="true" aria-live="polite">
      <span className="visually-hidden">{label}</span>
      <Stack gap={2}>
        <Skeleton width="55%" height={14} />
        <Skeleton width="90%" height={12} />
        <Skeleton width="70%" height={12} />
      </Stack>
    </div>
  )
}
