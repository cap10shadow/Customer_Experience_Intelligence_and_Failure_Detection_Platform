import { useCallback, useMemo, useState, type ReactNode } from 'react'

import {
  AdministrationContext,
  type AdministrationContextValue,
  type AdministrationSectionId,
} from './AdministrationContext'

export interface AdministrationContextProviderProps {
  children: ReactNode
}

/**
 * Owns only presentation state for one Administration reading session --
 * which section is active, which are expanded, and which Intelligence
 * Configuration item is currently in its editing state. Deliberately does
 * NOT own users, roles, permissions, integrations, policies, audit
 * history, or platform status -- that is business data a future step
 * supplies as illustrative or real props, exactly as `DashboardContext`,
 * `InvestigationContext`, `RecommendationContext`, and `AnalyticsContext`
 * each already establish for their own workspace. No fetching, no
 * configuration persistence, no business logic.
 */
export function AdministrationContextProvider({ children }: AdministrationContextProviderProps) {
  const [activeSection, setActiveSectionState] = useState<AdministrationSectionId>('platform-overview')
  const [expandedSections, setExpandedSections] = useState<ReadonlySet<AdministrationSectionId>>(() => new Set())
  const [selectedConfigurationId, setSelectedConfigurationId] = useState<string | null>(null)

  const setActiveSection = useCallback((section: AdministrationSectionId) => setActiveSectionState(section), [])

  const toggleSectionExpanded = useCallback((section: AdministrationSectionId) => {
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

  const selectConfigurationItem = useCallback(
    (configurationId: string | null) => setSelectedConfigurationId(configurationId),
    [],
  )

  const value = useMemo<AdministrationContextValue>(
    () => ({
      activeSection,
      expandedSections,
      selectedConfigurationId,
      setActiveSection,
      toggleSectionExpanded,
      selectConfigurationItem,
    }),
    [activeSection, expandedSections, selectedConfigurationId, setActiveSection, toggleSectionExpanded, selectConfigurationItem],
  )

  return <AdministrationContext.Provider value={value}>{children}</AdministrationContext.Provider>
}
