import { Grid, Stack } from '@/shared/components/layout'

import { AdministrationEmptyState, AdministrationSection, AdministrationSubsectionHeading } from '../foundation'
import type { ConnectedService, PlatformOverviewFact, ServiceHealth } from '../../types'
import { ConnectedServiceCard } from './ConnectedServiceCard'
import { FactCard } from './FactCard'

/**
 * Facts with no real backend source today -- unlike "Platform status"
 * (Step 7.X A-02, computed from real service health below), nothing in
 * the platform currently exposes a real version/environment/license/
 * config-timestamp capability, so these remain explicitly illustrative
 * rather than fabricated-to-look-real.
 */
const ILLUSTRATIVE_FACTS: PlatformOverviewFact[] = [
  { id: 'version', label: 'Platform version', value: '2026.8.0 (illustrative)' },
  { id: 'environment', label: 'Environment', value: 'Production (illustrative)' },
  { id: 'edition', label: 'License / edition', value: 'Enterprise (illustrative)' },
  { id: 'last-configuration-update', label: 'Last configuration update', value: '2026-08-05 09:14 UTC (illustrative)' },
]

const CONNECTED_SERVICES: ConnectedService[] = [
  { id: 'primary-database', name: 'Primary database', description: 'PostgreSQL instance the platform persists all operational and administrative data to.' },
  { id: 'event-infrastructure', name: 'Event infrastructure', description: 'In-process event consumer/publisher backing the platform’s execution lifecycle (see EVAL-001).' },
]

/** Shape-only placeholder -- never rendered as visible text; see SupportingEvidence's identical LOADING_SHAPE_ITEMS precedent. */
const LOADING_SERVICE_SHAPE: ServiceHealth[] = Array.from({ length: 9 }, (_, index) => ({
  id: `loading-${index}`,
  name: '',
  status: 'healthy',
  detail: '',
}))

export interface PlatformOverviewProps {
  /** Real, factual "N/M services healthy" summary (Step 7.X A-02) -- undefined only before the first fetch resolves. */
  platformStatusSummary?: string
  /** Real per-service reachability, sourced from each service's own `/health` endpoint via the Gateway (Step 7.X A-02) -- undefined only before the first fetch resolves. */
  services?: ServiceHealth[]
  isLoading?: boolean
}

/**
 * "What is the current operational state of the platform?" -- descriptive
 * only. No actions. No recommendations. State register: a compact,
 * scannable reference an administrator returns to, not a narrative read
 * once. Connected Services (platform infrastructure dependencies) is
 * deliberately labeled and framed to never be confused with Data Sources
 * & Integrations' Connected Systems (ADM-006), and is itself distinct from
 * "Service health" below: Connected Services describes what the platform
 * depends on, Service health reports the real reachability of the
 * platform's own backend services.
 */
export function PlatformOverview({ platformStatusSummary, services, isLoading = false }: PlatformOverviewProps) {
  const statusFact: PlatformOverviewFact = { id: 'status', label: 'Platform status', value: platformStatusSummary ?? '' }
  const facts = [statusFact, ...ILLUSTRATIVE_FACTS]
  const resolvedServices = services ?? LOADING_SERVICE_SHAPE

  return (
    <AdministrationSection
      id="platform-overview"
      title="Platform Overview"
      description="The current operational state of the platform."
      register="state"
    >
      <Stack gap={6}>
        <Grid minColumnWidth={200}>
          {facts.map((fact) => (
            <FactCard
              key={fact.id}
              fact={fact}
              isLoading={isLoading || (fact.id === 'status' && !platformStatusSummary)}
            />
          ))}
        </Grid>

        <Stack gap={4}>
          <AdministrationSubsectionHeading
            title="Service health"
            description="The current reachability of every backend service, checked directly against each service's own health endpoint."
          />
          {!isLoading && services && services.length === 0 ? (
            <AdministrationEmptyState
              title="No service health data available"
              description="Service health could not be retrieved for this request."
            />
          ) : (
            <Grid minColumnWidth={200}>
              {resolvedServices.map((service) => (
                <FactCard
                  key={service.id}
                  fact={{
                    id: service.id,
                    label: service.name,
                    value: service.status === 'healthy' ? 'Healthy' : 'Unavailable',
                  }}
                  isLoading={isLoading || !services}
                />
              ))}
            </Grid>
          )}
        </Stack>

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
