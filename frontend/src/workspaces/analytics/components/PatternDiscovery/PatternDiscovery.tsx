import { Stack } from '@/shared/components/layout'

import { AnalyticsSection } from '../foundation'
import type { PatternNarrative } from '../../types'
import { PatternCard } from './PatternCard'

const PATTERNS: PatternNarrative[] = [
  {
    id: 'checkout-failures-recur',
    headline: 'Checkout-related complaints tend to recur around provider changes',
    narrative: 'Several past incidents involving checkout failures have coincided with changes on the payment provider side, not just the most recent one.',
    evidence: 'Supported by recurring correlation between provider-change timing and checkout incident timing.',
  },
]

export interface PatternDiscoveryProps {
  isLoading?: boolean
}

/** "What keeps happening?" -- Headline → Narrative → Supporting Evidence, never a bare pattern list or a chart wall (UX-008). */
export function PatternDiscovery({ isLoading = false }: PatternDiscoveryProps) {
  return (
    <AnalyticsSection id="pattern-discovery" title="Pattern Discovery" description="What keeps happening?">
      <Stack gap={4}>
        {PATTERNS.map((pattern) => (
          <PatternCard key={pattern.id} pattern={pattern} isLoading={isLoading} />
        ))}
      </Stack>
    </AnalyticsSection>
  )
}
