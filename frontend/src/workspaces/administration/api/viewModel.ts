import type { ServiceHealth } from '../types'
import type { AdministrationApiOverviewResponse } from './types'

/** The Administration workspace's own view model for its one real data source so far: Platform Overview's service health. */
export interface AdministrationViewModel {
  services: ServiceHealth[]
  /** A factual count only ("N/M services healthy") -- never a severity/evaluative claim beyond what the real per-service statuses already state. */
  platformStatusSummary: string
  warnings: string[]
}

export function toAdministrationViewModel(response: AdministrationApiOverviewResponse): AdministrationViewModel {
  const healthyCount = response.services.filter((service) => service.status === 'healthy').length
  return {
    services: response.services,
    platformStatusSummary: `${healthyCount}/${response.services.length} services healthy`,
    warnings: response.warnings,
  }
}
