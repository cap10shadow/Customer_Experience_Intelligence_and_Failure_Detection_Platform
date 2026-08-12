import { Stack } from '@/shared/components/layout'

import { RecommendationSection } from '../foundation'
import type { RationaleReason } from '../../types'
import { RationaleCard } from './RationaleCard'
import { TraceabilityPanel } from './TraceabilityPanel'

const DEFAULT_REASON: RationaleReason = {
  headline: 'The timing lines up with a known change',
  explanation:
    'The investigation identified a recent payment provider change as the most likely cause of the checkout failures. Reviewing that change is the most direct way to confirm or rule it out before further action is taken.',
}

export interface RecommendationRationaleProps {
  /** Defaults to illustrative content -- RecommendationsWorkspace passes a real, Gateway-sourced reason here instead of editing this component. */
  reason?: RationaleReason
  isLoading?: boolean
}

/** "Why is this recommended?" -- references the Investigation's own findings rather than restating them. */
export function RecommendationRationale({ reason = DEFAULT_REASON, isLoading = false }: RecommendationRationaleProps) {
  return (
    <RecommendationSection id="rationale" title="Recommendation Rationale" description="Why is this recommended?">
      <Stack gap={4}>
        <RationaleCard reason={reason} isLoading={isLoading} />
        {!isLoading ? <TraceabilityPanel /> : null}
      </Stack>
    </RecommendationSection>
  )
}
