import { createContext } from 'react'

/**
 * The five narrative sections, in their fixed reading order. Investigation
 * is not its own entity (see workspace doc comment) -- this id set exists
 * purely to track presentation state (which section is active, which are
 * expanded), never a persisted or business concept.
 */
export type InvestigationSectionId = 'observation' | 'evidence' | 'root-cause' | 'business-impact' | 'recommended-next-step'

export const INVESTIGATION_SECTION_ORDER: InvestigationSectionId[] = [
  'observation',
  'evidence',
  'root-cause',
  'business-impact',
  'recommended-next-step',
]

export interface InvestigationContextValue {
  /**
   * The single Incident this investigation presents. Investigation has
   * no identity of its own -- this is a reference, not a foreign key on
   * a new entity. `null` until a future step wires real navigation
   * (e.g. a route param) from the Dashboard's Operational Story cards.
   */
  incidentId: string | null
  activeSection: InvestigationSectionId
  expandedSections: ReadonlySet<InvestigationSectionId>
  selectedEvidenceId: string | null
  setActiveSection: (section: InvestigationSectionId) => void
  toggleSectionExpanded: (section: InvestigationSectionId) => void
  selectEvidence: (evidenceId: string | null) => void
}

export const InvestigationContext = createContext<InvestigationContextValue | undefined>(undefined)
