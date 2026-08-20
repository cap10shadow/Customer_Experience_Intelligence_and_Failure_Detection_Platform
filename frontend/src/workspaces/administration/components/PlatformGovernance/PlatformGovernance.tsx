import { AdvisoryNotice } from '@/shared/components/feedback'
import { Stack } from '@/shared/components/layout'

import { AdministrationSection, AdministrationStatusBadge } from '../foundation'
import type { GovernancePolicy } from '../../types'
import { GovernancePolicyCard } from './GovernancePolicyCard'

const POLICIES: GovernancePolicy[] = [
  {
    id: 'retention-policy',
    headline: 'Operational data is retained for 24 months',
    statement: 'Complaint, incident, and recommendation records are retained for 24 months from creation to support longitudinal operational analysis, after which they are eligible for archival per the organization’s compliance requirements.',
  },
  {
    id: 'configuration-change-policy',
    headline: 'Intelligence configuration changes require administrator review',
    statement: 'Changes to detection rules, classification thresholds, and alert policies are reviewed by a platform administrator before taking effect, so downstream intelligence never shifts without deliberate, accountable oversight.',
  },
  {
    id: 'security-posture',
    headline: 'Access is governed by single sign-on and role-based permissions',
    statement: 'Every user authenticates through the organization’s identity provider, and every action is scoped by the role and permission group assigned to that user -- consistent with the platform’s Human Oversight principle.',
  },
]

export interface PlatformGovernanceProps {
  isLoading?: boolean
}

/**
 * "What governs how the platform operates?" -- ADM-001: organizational
 * policy, described in calm narrative prose. Never a configuration
 * control, and never audit history -- Platform Governance states what
 * the organization has committed to; Audit & Change History records
 * whether and when that commitment was acted on.
 */
export function PlatformGovernance({ isLoading = false }: PlatformGovernanceProps) {
  return (
    <AdministrationSection
      id="platform-governance"
      title="Platform Governance"
      description="What governs how the platform operates?"
      register="record"
      statusBadge={<AdministrationStatusBadge isLive={false} />}
    >
      <Stack gap={4}>
        {/* These read as commitments the organization has actually made
            (a 24-month retention policy, an SSO-governed security
            posture). None is configured or enforced anywhere in the
            platform, and retention duration is explicitly an open
            compliance decision -- so the copy is disclosed as example
            policy language rather than presented as binding. */}
        <AdvisoryNotice
          title="Illustrative content — not policy this platform enforces"
          description="The statements below are example policy language showing how governance commitments would be presented. No retention schedule, configuration-review workflow, or single sign-on is configured or enforced by the platform today."
        />
        <div>
          {POLICIES.map((policy) => (
            <GovernancePolicyCard key={policy.id} policy={policy} isLoading={isLoading} />
          ))}
        </div>
      </Stack>
    </AdministrationSection>
  )
}
