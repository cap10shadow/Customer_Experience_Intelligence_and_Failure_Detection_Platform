import type {
  CriticalSituation,
  DecisionOpportunity,
  FocusArea,
  HealthIndicator,
  KeyChange,
  OperationalStateLevel,
  OperationalStory,
} from '../types'
import type { DashboardApiResponse } from './types'

/** The Dashboard workspace's own view model -- what DashboardWorkspace actually hands down to its four sections. */
export interface DashboardViewModel {
  operationalStatus: {
    level: OperationalStateLevel
    summary: string
  }
  healthIndicators: HealthIndicator[]
  criticalSituations: CriticalSituation[]
  keyChanges: KeyChange[]
  focusAreas: FocusArea[]
  decisionOpportunities: DecisionOpportunity[]
  operationalStories: OperationalStory[]
  warnings: string[]
}

/**
 * Adapts the Gateway's DashboardResponse into the Dashboard workspace's
 * view model. Deliberately thin: the Gateway DTO's shape was designed
 * against these same presentation types (see ./types.ts), so this
 * mapping is mostly a regrouping of `operationalBrief`'s fields rather
 * than a field-by-field transformation -- there is no naming/casing/unit
 * mismatch left to reconcile here.
 */
export function toDashboardViewModel(response: DashboardApiResponse): DashboardViewModel {
  return {
    operationalStatus: {
      level: response.operationalBrief.level,
      summary: response.operationalBrief.summary,
    },
    healthIndicators: response.operationalBrief.healthIndicators,
    criticalSituations: response.operationalBrief.criticalSituations,
    keyChanges: response.operationalBrief.keyChanges,
    focusAreas: response.operationalBrief.focusAreas,
    decisionOpportunities: response.decisionSummary,
    operationalStories: response.investigationEntryPoints,
    warnings: response.warnings,
  }
}
