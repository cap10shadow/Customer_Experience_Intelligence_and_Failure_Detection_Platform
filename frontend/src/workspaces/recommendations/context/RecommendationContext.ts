import { createContext } from 'react'

/** The seven sections, in fixed reading order. */
export type RecommendationSectionId =
  | 'overview'
  | 'rationale'
  | 'alternative-options'
  | 'expected-outcome'
  | 'risk-assessment'
  | 'decision'
  | 'lifecycle'

export const RECOMMENDATION_SECTION_ORDER: RecommendationSectionId[] = [
  'overview',
  'rationale',
  'alternative-options',
  'expected-outcome',
  'risk-assessment',
  'decision',
  'lifecycle',
]

export interface RecommendationContextValue {
  /** This workspace's own identity. */
  recommendationId: string | null
  /**
   * A reference to the originating Incident only -- never a separate
   * "investigationId". Investigation has no identity of its own (see
   * `workspaces/investigations`'s own context); it is the presentation
   * of an Incident, so the only thing worth referencing back to is the
   * Incident itself.
   */
  incidentId: string | null
  activeSection: RecommendationSectionId
  expandedSections: ReadonlySet<RecommendationSectionId>
  setActiveSection: (section: RecommendationSectionId) => void
  toggleSectionExpanded: (section: RecommendationSectionId) => void
}

export const RecommendationContext = createContext<RecommendationContextValue | undefined>(undefined)
