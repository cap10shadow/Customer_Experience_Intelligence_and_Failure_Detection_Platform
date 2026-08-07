import { Grid, Stack } from '@/shared/components/layout'

import { AdministrationSection, AdministrationSubsectionHeading } from '../foundation'
import type { ConnectedService, PlatformOverviewFact } from '../../types'
import { ConnectedServiceCard } from './ConnectedServiceCard'
import { FactCard } from './FactCard'

const FACTS: PlatformOverviewFact[] = [
  { id: 'version', label: 'Platform version', value: '2026.8.0' },
  { id: 'environment', label: 'Environment', value: 'Production' },
  { id: 'status', label: 'Platform status', value: 'Operating normally' },
  { id: 'edition', label: 'License / edition', value: 'Enterprise (illustrative)' },
  { id: 'last-configuration-update', label: 'Last configuration update', value: '2026-08-05 09:14 UTC' },
]

const CONNECTED_SERVICES: ConnectedService[] = [
  { id: 'primary-database', name: 'Primary database', description: 'PostgreSQL instance the platform persists all operational and administrative data to.' },
  { id: 'event-infrastructure', name: 'Event infrastructure', description: 'In-process event consumer/publisher backing the platform’s execution lifecycle (see EVAL-001).' },
]

export interface PlatformOverviewProps {
  isLoading?: boolean
}

/**
 * "What is the current operational state of the platform?" -- descriptive
 * only. No actions. No recommendations. State register: a compact,
 * scannable reference an administrator returns to, not a narrative read
 * once. Connected Services (platform infrastructure dependencies) is
 * deliberately labeled and framed to never be confused with Data Sources
 * & Integrations' Connected Systems (ADM-006).
 */
export function PlatformOverview({ isLoading = false }: PlatformOverviewProps) {
  return (
    <AdministrationSection
      id="platform-overview"
      title="Platform Overview"
      description="The current operational state of the platform."
      register="state"
    >
      <Stack gap={6}>
        <Grid minColumnWidth={200}>
          {FACTS.map((fact) => (
            <FactCard key={fact.id} fact={fact} isLoading={isLoading} />
          ))}
        </Grid>

        <Stack gap={4}>
          <AdministrationSubsectionHeading
            title="Connected Services"
            description="Platform infrastructure this instance depends on -- not the external systems your organization connects and integrates, which are governed separately under Data Sources & Integrations."
          />
          <Grid minColumnWidth={240}>
            {CONNECTED_SERVICES.map((service) => (
              <ConnectedServiceCard key={service.id} service={service} isLoading={isLoading} />
            ))}
          </Grid>
        </Stack>
      </Stack>
    </AdministrationSection>
  )
}
