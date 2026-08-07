import { Skeleton } from '@/shared/components/feedback'
import { Stack } from '@/shared/components/layout'

export interface AdministrationLoadingStateProps {
  label: string
}

/** Skeleton-first loading, matching the treatment established in Dashboard (Step 2), Investigation (Step 3), Recommendation (Step 4), and Analytics (Step 5). */
export function AdministrationLoadingState({ label }: AdministrationLoadingStateProps) {
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
