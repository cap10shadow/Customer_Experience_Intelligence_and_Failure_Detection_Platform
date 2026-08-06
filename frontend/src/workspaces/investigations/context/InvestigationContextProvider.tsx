import { useCallback, useMemo, useState, type ReactNode } from 'react'

import {
  InvestigationContext,
  type InvestigationContextValue,
  type InvestigationSectionId,
} from './InvestigationContext'

export interface InvestigationContextProviderProps {
  /** The Incident this investigation presents -- `null` until a future step supplies one via routing. */
  incidentId?: string | null
  children: ReactNode
}

/**
 * Owns only presentation state for one investigation reading session --
 * which section is active, which are expanded, which evidence is
 * selected. No backend state, no business state, no fetching: this is
 * the same architectural role Dashboard's `DashboardContextProvider`
 * plays for the Dashboard, scoped to a single Incident instead of a
 * cross-cutting scope.
 */
export function InvestigationContextProvider({ incidentId = null, children }: InvestigationContextProviderProps) {
  const [activeSection, setActiveSectionState] = useState<InvestigationSectionId>('observation')
  const [expandedSections, setExpandedSections] = useState<ReadonlySet<InvestigationSectionId>>(() => new Set())
  const [selectedEvidenceId, setSelectedEvidenceId] = useState<string | null>(null)

  const setActiveSection = useCallback((section: InvestigationSectionId) => setActiveSectionState(section), [])

  const toggleSectionExpanded = useCallback((section: InvestigationSectionId) => {
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

  const selectEvidence = useCallback((evidenceId: string | null) => setSelectedEvidenceId(evidenceId), [])

  const value = useMemo<InvestigationContextValue>(
    () => ({
      incidentId,
      activeSection,
      expandedSections,
      selectedEvidenceId,
      setActiveSection,
      toggleSectionExpanded,
      selectEvidence,
    }),
    [incidentId, activeSection, expandedSections, selectedEvidenceId, setActiveSection, toggleSectionExpanded, selectEvidence],
  )

  return <InvestigationContext.Provider value={value}>{children}</InvestigationContext.Provider>
}
