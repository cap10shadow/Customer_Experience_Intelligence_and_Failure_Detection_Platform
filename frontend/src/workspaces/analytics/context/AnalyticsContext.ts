import { createContext } from 'react'

import type { AnalysisPeriod } from '../types'

/** The six narrative sections, in fixed reading order. */
export type AnalyticsSectionId =
  | 'executive-overview'
  | 'trend-analysis'
  | 'pattern-discovery'
  | 'recommendation-effectiveness'
  | 'organizational-insights'
  | 'strategic-opportunities'

export const ANALYTICS_SECTION_ORDER: AnalyticsSectionId[] = [
  'executive-overview',
  'trend-analysis',
  'pattern-discovery',
  'recommendation-effectiveness',
  'organizational-insights',
  'strategic-opportunities',
]

export interface AnalyticsContextValue {
  /** UX-005: the one shared workspace-level scope every section reads, never restates. */
  selectedAnalysisPeriod: AnalysisPeriod
  activeSection: AnalyticsSectionId
  expandedSections: ReadonlySet<AnalyticsSectionId>
  selectedInsightId: string | null
  setAnalysisPeriod: (period: AnalysisPeriod) => void
  setActiveSection: (section: AnalyticsSectionId) => void
  toggleSectionExpanded: (section: AnalyticsSectionId) => void
  selectInsight: (insightId: string | null) => void
}

export const AnalyticsContext = createContext<AnalyticsContextValue | undefined>(undefined)
