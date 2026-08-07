import { Grid, Stack } from '@/shared/components/layout'

import { AdministrationEmptyState, AdministrationSection, AdministrationSubsectionHeading } from '../foundation'
import type { ConnectedSystem } from '../../types'
import { ConnectedSystemCard } from './ConnectedSystemCard'

const DEFAULT_CONNECTED_SYSTEMS: ConnectedSystem[] = [
  {
    id: 'crm',
    name: 'Customer relationship management system',
    description: 'Source of customer complaint records ingested into the platform.',
    connectionHealth: 'Connected',
  },
  {
    id: 'support-desk',
    name: 'Support desk',
    description: 'Source of support ticket records correlated against operational incidents.',
    connectionHealth: 'Connected',
  },
]

export interface DataSourcesIntegrationsProps {
  isLoading?: boolean
  /** Illustrative business data -- defaults to two connected systems; pass an empty array to exercise the honest empty state. */
  systems?: ConnectedSystem[]
}

/**
 * "How does operational data enter the platform?" -- Connected Systems
 * (external business systems), integration configuration, API
 * connections, and import pipelines. ADM-006: labeled and framed to
 * never be confused with Platform Overview's Connected Services
 * (platform infrastructure dependencies). Connection Health is
 * descriptive only -- never live monitoring, never operational
 * monitoring, never DevOps.
 */
export function DataSourcesIntegrations({ isLoading = false, systems = DEFAULT_CONNECTED_SYSTEMS }: DataSourcesIntegrationsProps) {
  return (
    <AdministrationSection
      id="data-sources-integrations"
      title="Data Sources & Integrations"
      description="How does operational data enter the platform?"
      register="state"
    >
      <Stack gap={4}>
        <AdministrationSubsectionHeading
          title="Connected Systems"
          description="External business systems your organization connects and integrates for operational data -- not platform infrastructure, which is listed separately under Platform Overview's Connected Services."
        />
        {systems.length === 0 && !isLoading ? (
          <AdministrationEmptyState
            title="No external systems are connected yet"
            description="Once your organization connects a system (a CRM, a support desk, an operational data feed), it will appear here alongside its integration configuration."
          />
        ) : (
          <Grid minColumnWidth={260}>
            {(isLoading ? DEFAULT_CONNECTED_SYSTEMS : systems).map((system) => (
              <ConnectedSystemCard key={system.id} system={system} isLoading={isLoading} />
            ))}
          </Grid>
        )}
      </Stack>
    </AdministrationSection>
  )
}
