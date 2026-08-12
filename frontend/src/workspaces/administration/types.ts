/** Platform Overview -- descriptive only. No actions. No recommendations. */
export interface PlatformOverviewFact {
  id: string
  label: string
  value: string
}

/**
 * A backend service's real, just-checked reachability (Step 7.X A-02) --
 * sourced from that service's own existing `/health` endpoint via the
 * Gateway's `/administration/overview` aggregation. Not a production
 * observability/uptime-history capability: no metrics storage, no
 * historical SLA calculation, just the current reachability.
 */
export type ServiceHealthStatus = 'healthy' | 'unavailable'

export interface ServiceHealth {
  id: string
  name: string
  status: ServiceHealthStatus
  detail: string
}

/**
 * Platform infrastructure dependencies -- e.g. the database or message
 * infrastructure this service itself runs on. Deliberately distinct from
 * `ConnectedSystem` (Data Sources & Integrations' external business
 * systems): ADM-006 requires this distinction to be visually obvious,
 * not just organizationally true.
 */
export interface ConnectedService {
  id: string
  name: string
  description: string
}

/** User & Access Management -- governs who can use the platform, never usage analytics or behavior. */
export interface AccessArea {
  id: string
  label: string
  summary: string
}

/**
 * An external business system integrated for operational data -- e.g. a
 * CRM or support desk. Deliberately distinct from `ConnectedService`
 * (Platform Overview's infrastructure dependencies).
 */
export interface ConnectedSystem {
  id: string
  name: string
  description: string
  /** Descriptive only -- never live monitoring, never operational monitoring, never DevOps. */
  connectionHealth: string
}

/**
 * ADM-002: every configurable item is presented in this fixed sequence --
 * whatItIs -> governs -> currentValue -> the edit affordance. The type
 * itself carries the sequence as named fields so no component can
 * accidentally reorder them.
 */
export interface ConfigurationItem {
  id: string
  name: string
  whatItIs: string
  governs: string
  currentValue: string
}

/** Platform Governance -- calm organizational-policy narrative, never a configuration control and never audit history. */
export interface GovernancePolicy {
  id: string
  headline: string
  statement: string
}

/**
 * A single, permanent audit ledger entry. `occurredAt` is always an
 * absolute timestamp (never a relative "2m ago" string) -- ADM-003
 * forbids activity-feed conventions, and relative time is one of them.
 */
export interface AuditEntry {
  id: string
  occurredAt: string
  actor: string
  action: string
  from: string
  to: string
}
