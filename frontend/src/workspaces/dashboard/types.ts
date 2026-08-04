import type { IconName } from '@/shared/icons'
import type { StatusTone } from '@/shared/components/utility'

/**
 * The Dashboard's operational state vocabulary -- the architectural
 * foundation "Operationally Healthy / Elevated Risk / Critical" calls
 * for. Every subsection that communicates status (OperationalStatus,
 * OperationalHealthSnapshot) maps onto this same three-level scale, so
 * "critical" means the same thing everywhere on the Dashboard.
 */
export type OperationalStateLevel = 'stable' | 'elevated' | 'critical'

export const OPERATIONAL_STATE_TONE: Record<OperationalStateLevel, StatusTone> = {
  stable: 'success',
  elevated: 'warning',
  critical: 'critical',
}

/** Matches the Overall Operational Status examples given in the frozen architecture verbatim. */
export const OPERATIONAL_STATE_LABEL: Record<OperationalStateLevel, string> = {
  stable: 'Operations Stable',
  elevated: 'Operations Under Elevated Risk',
  critical: 'Critical Operational Issues Detected',
}

export type TrendDirection = 'up' | 'down' | 'steady'

export const TREND_ICON: Record<TrendDirection, IconName> = {
  up: 'trendUp',
  down: 'trendDown',
  steady: 'trendFlat',
}

export interface CriticalSituation {
  id: string
  headline: string
  detail: string
}

export interface KeyChange {
  id: string
  headline: string
  direction: TrendDirection
  detail: string
}

export interface FocusArea {
  id: string
  headline: string
  reason: string
}

export interface HealthIndicator {
  id: string
  label: string
  level: OperationalStateLevel
  trend: TrendDirection
  detail: string
}

/** Business importance of a Decision Opportunity -- deliberately a separate scale from OperationalStateLevel: importance ranks judgment value, not operational severity. */
export type ImportanceLevel = 'high' | 'medium' | 'low'

export const IMPORTANCE_TONE: Record<ImportanceLevel, StatusTone> = {
  high: 'critical',
  medium: 'warning',
  low: 'info',
}

export const IMPORTANCE_LABEL: Record<ImportanceLevel, string> = {
  high: 'High business importance',
  medium: 'Medium business importance',
  low: 'Low business importance',
}

export interface DecisionOpportunity {
  id: string
  headline: string
  importance: ImportanceLevel
  reason: string
  nextDecision: string
  drillDownPath?: string
  drillDownLabel?: string
}

/**
 * The Dashboard's presentation model of an Incident's lifecycle --
 * NOT a new domain entity. See InvestigationEntryPoints: an Operational
 * Story never exposes a raw Incident/Complaint id, only the narrative.
 */
export interface OperationalStory {
  id: string
  headline: string
  situation: string
  significance: string
  direction: string
  context: string
  drillDownPath?: string
  drillDownLabel?: string
}

export interface EvidenceItem {
  id: string
  headline: string
  description: string
}
