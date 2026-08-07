import { useCallback, useMemo, useState, type ReactNode } from 'react'

import type { AnalysisPeriod } from '../types'
import { AnalyticsContext, type AnalyticsContextValue, type AnalyticsSectionId } from './AnalyticsContext'

export interface AnalyticsContextProviderProps {
  defaultAnalysisPeriod?: AnalysisPeriod
  children: ReactNode
}

/**
 * Owns only presentation state for one Analytics reading session --
 * which section is active, which are expanded, which insight is
 * selected, and the one shared scope (UX-005) every section reads
 * rather than restating. Deliberately does not hold metrics, trend
 * data, or recommendation outcomes -- those remain illustrative props
 * a future step supplies from real data, exactly as `DashboardContext`,
 * `InvestigationContext`, and `RecommendationContext` each already
 * establish for their own workspace.
 */
export function AnalyticsContextProvider({ defaultAnalysisPeriod = 'last-30-days', children }: AnalyticsContextProviderProps) {
  const [selectedAnalysisPeriod, setSelectedAnalysisPeriod] = useState<AnalysisPeriod>(defaultAnalysisPeriod)
  const [activeSection, setActiveSectionState] = useState<AnalyticsSectionId>('executive-overview')
  const [expandedSections, setExpandedSections] = useState<ReadonlySet<AnalyticsSectionId>>(() => new Set())
  const [selectedInsightId, setSelectedInsightId] = useState<string | null>(null)

  const setAnalysisPeriod = useCallback((period: AnalysisPeriod) => setSelectedAnalysisPeriod(period), [])
  const setActiveSection = useCallback((section: AnalyticsSectionId) => setActiveSectionState(section), [])

  const toggleSectionExpanded = useCallback((section: AnalyticsSectionId) => {
    setExpandedSections((current) => {
      const next = new Set(current)
      if (next.has(section)) {
        next.delete(section)
      } else {
        next.add(section)
      }
      return next
    })
  }, [])

  const selectInsight = useCallback((insightId: string | null) => setSelectedInsightId(insightId), [])

  const value = useMemo<AnalyticsContextValue>(
    () => ({
      selectedAnalysisPeriod,
      activeSection,
      expandedSections,
      selectedInsightId,
      setAnalysisPeriod,
      setActiveSection,
      toggleSectionExpanded,
      selectInsight,
    }),
    [
      selectedAnalysisPeriod,
      activeSection,
      expandedSections,
      selectedInsightId,
      setAnalysisPeriod,
      setActiveSection,
      toggleSectionExpanded,
      selectInsight,
    ],
  )

  return <AnalyticsContext.Provider value={value}>{children}</AnalyticsContext.Provider>
}
