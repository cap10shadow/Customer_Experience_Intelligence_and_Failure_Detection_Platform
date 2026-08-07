import { createContext } from 'react'

/** The six sections, in fixed reading order. */
export type AdministrationSectionId =
  | 'platform-overview'
  | 'user-access-management'
  | 'data-sources-integrations'
  | 'intelligence-configuration'
  | 'platform-governance'
  | 'audit-change-history'

export const ADMINISTRATION_SECTION_ORDER: AdministrationSectionId[] = [
  'platform-overview',
  'user-access-management',
  'data-sources-integrations',
  'intelligence-configuration',
  'platform-governance',
  'audit-change-history',
]

/**
 * The register each section belongs to (State / Configuration / Record),
 * used only to drive the subtle presentation rhythm ADM-005 calls for --
 * never a navigation grouping, never a data source for business logic.
 */
export type AdministrationRegister = 'state' | 'configuration' | 'record'

export const ADMINISTRATION_SECTION_REGISTER: Record<AdministrationSectionId, AdministrationRegister> = {
  'platform-overview': 'state',
  'user-access-management': 'state',
  'data-sources-integrations': 'state',
  'intelligence-configuration': 'configuration',
  'platform-governance': 'record',
  'audit-change-history': 'record',
}

export interface AdministrationContextValue {
  activeSection: AdministrationSectionId
  expandedSections: ReadonlySet<AdministrationSectionId>
  /** Which Intelligence Configuration item, if any, is currently in its editing state -- ADM-002's "inspection is always the default state." */
  selectedConfigurationId: string | null
  setActiveSection: (section: AdministrationSectionId) => void
  toggleSectionExpanded: (section: AdministrationSectionId) => void
  selectConfigurationItem: (configurationId: string | null) => void
}

export const AdministrationContext = createContext<AdministrationContextValue | undefined>(undefined)
