import { Skeleton } from '@/shared/components/feedback'
import { Stack } from '@/shared/components/layout'

export interface RecommendationLoadingStateProps {
  label: string
}

/** Skeleton-first loading, matching the treatment established in Dashboard (Step 2) and Investigation (Step 3). Kept local for the same reason as `RecommendationSection`. */
export function RecommendationLoadingState({ label }: RecommendationLoadingStateProps) {
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
