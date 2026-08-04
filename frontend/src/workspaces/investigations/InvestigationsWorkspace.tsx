import { SectionContainer, Stack } from '@/shared/components/layout'
import { PlaceholderCard } from '@/shared/components/feedback'
import { WorkspaceContainer } from '@/shared/components/page'

const INVESTIGATION_STAGES = [
  'Complaint',
  'Incident',
  'Timeline',
  'Root Cause',
  'Business Impact',
  'Evidence',
  'Recommendations',
]

/**
 * Investigations -- understanding operational problems, from a raw
 * complaint through to the recommendations that address it.
 * Recommendations appear contextually inside an investigation here (a
 * future step); users are never sent to the Recommendations workspace
 * just to see recommendations related to what they're investigating.
 */
export function InvestigationsWorkspace() {
  return (
    <WorkspaceContainer
      title="Investigations"
      description="Understand operational problems from complaint through to recommendation."
    >
      <SectionContainer
        title="Investigation flow"
        description={`Every investigation follows the same path: ${INVESTIGATION_STAGES.join(' → ')}.`}
      >
        <Stack>
          <PlaceholderCard
            title="Investigation list"
            description="A future step will list active and historical investigations here, each drilling into its own Complaint → Recommendations flow."
          />
        </Stack>
      </SectionContainer>
    </WorkspaceContainer>
  )
}
