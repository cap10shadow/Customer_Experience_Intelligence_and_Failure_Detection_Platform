import { Stack } from '@/shared/components/layout'
import { WorkspaceContainer } from '@/shared/components/page'

import { DecisionSummarySection } from './components/DecisionSummarySection'
import { InvestigationEntryPointsSection } from './components/InvestigationEntryPointsSection'
import { OperationalAnalyticsSection } from './components/OperationalAnalyticsSection'
import { OperationalBriefSection } from './components/OperationalBriefSection'

/**
 * Operational Intelligence Dashboard -- the application home. Not a KPI
 * dashboard: it answers "what changed, why does it matter, what needs
 * attention, and where do I go next" before any supporting analytics,
 * via four architectural sections rendered in that fixed order.
 */
export function DashboardWorkspace() {
  return (
    <WorkspaceContainer
      title="Operational Intelligence Dashboard"
      description="Immediate operational awareness -- what changed, why it matters, and where to go next."
    >
      <Stack gap={10}>
        <OperationalBriefSection />
        <DecisionSummarySection />
        <InvestigationEntryPointsSection />
        <OperationalAnalyticsSection />
      </Stack>
    </WorkspaceContainer>
  )
}
