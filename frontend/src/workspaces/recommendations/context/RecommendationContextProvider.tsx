import { useCallback, useMemo, useState, type ReactNode } from 'react'

import {
  RecommendationContext,
  type RecommendationContextValue,
  type RecommendationSectionId,
} from './RecommendationContext'

export interface RecommendationContextProviderProps {
  recommendationId?: string | null
  incidentId?: string | null
  children: ReactNode
}

/**
 * Owns only presentation state for one recommendation reading session --
 * which section is active, which are expanded -- plus the two reference
 * ids the workspace is scoped to. Deliberately does NOT hold a
 * "lifecycle stage" value: the recommendation's actual status is
 * business data a future step supplies from real data, not a UI
 * concern this Context should own (see `RecommendationContext`'s own
 * doc comment).
 */
export function RecommendationContextProvider({
  recommendationId = null,
  incidentId = null,
  children,
}: RecommendationContextProviderProps) {
  const [activeSection, setActiveSectionState] = useState<RecommendationSectionId>('overview')
  const [expandedSections, setExpandedSections] = useState<ReadonlySet<RecommendationSectionId>>(() => new Set())

  const setActiveSection = useCallback((section: RecommendationSectionId) => setActiveSectionState(section), [])

  const toggleSectionExpanded = useCallback((section: RecommendationSectionId) => {
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

  const value = useMemo<RecommendationContextValue>(
    () => ({
      recommendationId,
      incidentId,
      activeSection,
      expandedSections,
      setActiveSection,
      toggleSectionExpanded,
    }),
    [recommendationId, incidentId, activeSection, expandedSections, setActiveSection, toggleSectionExpanded],
  )

  return <RecommendationContext.Provider value={value}>{children}</RecommendationContext.Provider>
}
