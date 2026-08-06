import { Stack } from '@/shared/components/layout'

import { RecommendationSection } from '../foundation'
import type { RationaleReason } from '../../types'
import { RationaleCard } from './RationaleCard'
import { TraceabilityPanel } from './TraceabilityPanel'

const REASON: RationaleReason = {
  headline: 'The timing lines up with a known change',
  explanation:
    'The investigation identified a recent payment provider change as the most likely cause of the checkout failures. Reviewing that change is the most direct way to confirm or rule it out before further action is taken.',
}

export interface RecommendationRationaleProps {
  isLoading?: boolean
}

/** "Why is this recommended?" -- references the Investigation's own findings rather than restating them. */
export function RecommendationRationale({ isLoading = false }: RecommendationRationaleProps) {
  return (
    <RecommendationSection id="rationale" title="Recommendation Rationale" description="Why is this recommended?">
      <Stack gap={4}>
        <RationaleCard reason={REASON} isLoading={isLoading} />
        {!isLoading ? <TraceabilityPanel /> : null}
      </Stack>
    </RecommendationSection>
  )
}
