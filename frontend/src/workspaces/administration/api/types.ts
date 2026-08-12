import type { ServiceHealthStatus } from '../types'

/**
 * Shape of GET /api/v1/administration/overview's response body
 * (backend/services/gateway_service/app/schemas/administration.py's
 * AdministrationOverviewResponse).
 */
export interface AdministrationApiServiceHealth {
  id: string
  name: string
  status: ServiceHealthStatus
  detail: string
}

export interface AdministrationApiOverviewResponse {
  services: AdministrationApiServiceHealth[]
  /** Human-readable notes about any service whose health check failed. Empty when every service is healthy. */
  warnings: string[]
}

/**
 * Shape of GET /api/v1/administration/intelligence-configuration's
 * response body (backend/services/gateway_service/app/schemas/
 * administration.py's IntelligenceConfigurationResponse). Read-only,
 * real Business Impact engine configuration (Step 7.X G-05) -- there is
 * deliberately no corresponding write/PATCH shape anywhere in this
 * module.
 */
export interface AdministrationApiConfigurationItem {
  id: string
  name: string
  whatItIs: string
  governs: string
  currentValue: string
}

export interface AdministrationApiIntelligenceConfigurationResponse {
  items: AdministrationApiConfigurationItem[]
}
