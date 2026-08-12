import type { ConfigurationItem, ServiceHealth } from '../types'
import type { AdministrationApiIntelligenceConfigurationResponse, AdministrationApiOverviewResponse } from './types'

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

/** Intelligence Configuration's view model (Step 7.X G-05) -- real, read-only Business Impact configuration items only. */
export interface IntelligenceConfigurationViewModel {
  items: ConfigurationItem[]
}

export function toIntelligenceConfigurationViewModel(
  response: AdministrationApiIntelligenceConfigurationResponse,
): IntelligenceConfigurationViewModel {
  return { items: response.items }
}
