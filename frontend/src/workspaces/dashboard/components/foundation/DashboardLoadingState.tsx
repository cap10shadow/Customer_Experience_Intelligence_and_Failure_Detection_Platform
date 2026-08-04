import { Skeleton } from '@/shared/components/feedback'
import { Stack } from '@/shared/components/layout'

export interface DashboardLoadingStateProps {
  /** Announced to screen readers (e.g. "Loading decision opportunities"). */
  label: string
}

/**
 * The skeleton-first loading treatment Dashboard cards use in place of
 * `LoadingContainer`'s spinner -- the frozen architecture explicitly
 * calls for skeleton placeholders as the *primary* Dashboard loading
 * experience (a spinner communicates "wait"; a skeleton also previews
 * shape, so layout never shifts once real content arrives). Mirrors
 * `LoadingContainer`'s aria-busy/aria-live contract so both read the
 * same way to assistive tech.
 */
export function DashboardLoadingState({ label }: DashboardLoadingStateProps) {
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
