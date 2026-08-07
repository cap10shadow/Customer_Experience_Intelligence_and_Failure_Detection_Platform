/**
 * A fixed set of illustrative period options -- not a date-range picker
 * or query builder. Analytics owns exactly one shared scope (UX-005);
 * this is its only dimension in this step.
 */
export type AnalysisPeriod = 'last-30-days' | 'last-quarter' | 'last-12-months'

export const ANALYSIS_PERIOD_LABEL: Record<AnalysisPeriod, string> = {
  'last-30-days': 'Last 30 days',
  'last-quarter': 'Last quarter',
  'last-12-months': 'Last 12 months',
}

/** Descriptive only -- Executive Overview must never evaluate or recommend, only observe what changed. */
export interface ObservationItem {
  id: string
  headline: string
  detail: string
}

/** Trend → Narrative → Supporting Evidence, never Chart → Interpretation. */
export interface TrendNarrative {
  id: string
  trend: string
  narrative: string
  evidence: string
}

/** Headline → Narrative → Supporting Evidence -- the same shape as TrendNarrative, never a bare list item or a chart. */
export interface PatternNarrative {
  id: string
  headline: string
  narrative: string
  evidence: string
}

/** A supported conclusion, not an observation and not a recommendation. */
export interface OrganizationalInsight {
  id: string
  headline: string
  explanation: string
}

/** An organization-level opportunity -- never an incident recommendation, never governed by Decision/Lifecycle. */
export interface StrategicOpportunity {
  id: string
  headline: string
  rationale: string
}
