import { AdvisoryNotice } from '@/shared/components/feedback'
import { Grid, Stack } from '@/shared/components/layout'

import { AdministrationSection, AdministrationStatusBadge } from '../foundation'
import type { AccessArea } from '../../types'
import { AccessAreaCard } from './AccessAreaCard'

const ACCESS_AREAS: AccessArea[] = [
  { id: 'users', label: 'Users', summary: '24 users provisioned across the organization.' },
  { id: 'roles', label: 'Roles', summary: '5 roles defined, each mapped to a fixed permission group.' },
  { id: 'permission-groups', label: 'Permission groups', summary: '5 permission groups govern what each role can view and configure.' },
  { id: 'authentication-provider', label: 'Authentication provider', summary: 'Single sign-on via the organization’s identity provider.' },
  { id: 'access-policies', label: 'Access policies', summary: 'Session timeout, password, and multi-factor requirements are enforced platform-wide.' },
]

export interface UserAccessManagementProps {
  isLoading?: boolean
}

/**
 * "Who can use the platform?" -- identity and permissions only, never
 * user analytics, activity monitoring, or behavioral analysis. State
 * register: compact, scannable reference.
 *
 * Presentation-only: no Gateway route exposes user/role administration,
 * so every card below is fixed illustrative copy. That was previously
 * stated only in this source file, which meant a person looking at the
 * rendered page saw specific counts and an SSO claim with nothing
 * marking them as not real -- and this platform authenticates with
 * email/password, not SSO. The `AdvisoryNotice` makes the disclosure
 * visible where it matters, rather than only to a reader of the code.
 */
export function UserAccessManagement({ isLoading = false }: UserAccessManagementProps) {
  return (
    <AdministrationSection
      id="user-access-management"
      title="User & Access Management"
      description="Who can use the platform?"
      register="state"
      statusBadge={<AdministrationStatusBadge isLive={false} />}
    >
      <Stack gap={4}>
        <AdvisoryNotice
          // Wording deliberately avoids "live"/"real-time"/"monitoring":
          // Administration must never read as an operational monitoring
          // surface (ADM-004, asserted by AdministrationWorkspace.test).
          title="Illustrative content — not this platform's actual access configuration"
          description="User counts, permission groups, and the authentication provider described below are fixed example copy. The platform has no user or role administration capability yet; real accounts and role assignments are managed outside the application, and this platform signs in with email and password rather than single sign-on."
        />
        <Grid minColumnWidth={220}>
          {ACCESS_AREAS.map((area) => (
            <AccessAreaCard key={area.id} area={area} isLoading={isLoading} />
          ))}
        </Grid>
      </Stack>
    </AdministrationSection>
  )
}
