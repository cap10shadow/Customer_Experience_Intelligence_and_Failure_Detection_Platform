import { Grid } from '@/shared/components/layout'

import { AdministrationSection } from '../foundation'
import type { AccessArea } from '../../types'
import { AccessAreaCard } from './AccessAreaCard'

const ACCESS_AREAS: AccessArea[] = [
  { id: 'users', label: 'Users', summary: '24 users provisioned across the organization (illustrative).' },
  { id: 'roles', label: 'Roles', summary: '5 roles defined, each mapped to a fixed permission group.' },
  { id: 'permission-groups', label: 'Permission groups', summary: '5 permission groups govern what each role can view and configure.' },
  { id: 'authentication-provider', label: 'Authentication provider', summary: 'Single sign-on via the organization’s identity provider.' },
  { id: 'access-policies', label: 'Access policies', summary: 'Session timeout, password, and multi-factor requirements are enforced platform-wide.' },
]

export interface UserAccessManagementProps {
  isLoading?: boolean
}

/** "Who can use the platform?" -- identity and permissions only, never user analytics, activity monitoring, or behavioral analysis. State register: compact, scannable reference. */
export function UserAccessManagement({ isLoading = false }: UserAccessManagementProps) {
  return (
    <AdministrationSection
      id="user-access-management"
      title="User & Access Management"
      description="Who can use the platform?"
      register="state"
    >
      <Grid minColumnWidth={220}>
        {ACCESS_AREAS.map((area) => (
          <AccessAreaCard key={area.id} area={area} isLoading={isLoading} />
        ))}
      </Grid>
    </AdministrationSection>
  )
}
