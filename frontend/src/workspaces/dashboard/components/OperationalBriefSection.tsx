import { SectionContainer } from '@/shared/components/layout'
import { PlaceholderCard } from '@/shared/components/feedback'

/**
 * Section 1 of the Operational Intelligence Dashboard: summarizes the
 * current operational situation ("what changed?"). Architectural
 * structure only -- the actual summary is real operational intelligence
 * a future step wires up from the backend, not fabricated here.
 */
export function OperationalBriefSection() {
  return (
    <SectionContainer
      title="Operational Brief"
      description="A summary of the current operational situation -- what changed since you last looked."
    >
      <PlaceholderCard
        title="Operational brief summary"
        description="A future step will populate this with a synthesized summary of recent operational changes."
      />
    </SectionContainer>
  )
}
