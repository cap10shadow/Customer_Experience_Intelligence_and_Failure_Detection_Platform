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
