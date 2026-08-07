import {
  ADMINISTRATION_SECTION_ORDER,
  ADMINISTRATION_SECTION_REGISTER,
  useAdministrationContext,
  type AdministrationSectionId,
} from '../../context'
import styles from './AdministrationNavigator.module.css'

const SECTION_LABEL: Record<AdministrationSectionId, string> = {
  'platform-overview': 'Platform Overview',
  'user-access-management': 'User & Access Management',
  'data-sources-integrations': 'Data Sources & Integrations',
  'intelligence-configuration': 'Intelligence Configuration',
  'platform-governance': 'Platform Governance',
  'audit-change-history': 'Audit & Change History',
}

/**
 * The persistent, always-visible map of Administration, structurally
 * mirroring `InvestigationNavigator`/`RecommendationNavigator`/
 * `AnalyticsNavigator` exactly -- real fragment links, `aria-current` on
 * click, no scroll-spy, same navigator family, not a new paradigm. A
 * single flat `<ol>`, same as every other workspace navigator: the
 * `data-register` attribute on each item drives ADM-005's subtle spacing
 * rhythm in CSS only -- it never becomes a second `<ol>`, a fieldset, an
 * `aria-labelledby` grouping, or any other structural grouping, and it
 * carries no persistent reference block (unlike Recommendation's Decision
 * reference or Analytics' Scope Indicator) because Administration has no
 * equivalent single piece of state to keep in view.
 */
export function AdministrationNavigator() {
  const { activeSection, setActiveSection } = useAdministrationContext()

  return (
    <nav aria-label="Administration sections" className={styles.navigator}>
      <ol className={styles.list}>
        {ADMINISTRATION_SECTION_ORDER.map((sectionId) => (
          <li key={sectionId} data-register={ADMINISTRATION_SECTION_REGISTER[sectionId]} className={styles.item}>
            <a
              href={`#${sectionId}`}
              onClick={() => setActiveSection(sectionId)}
              aria-current={activeSection === sectionId ? 'true' : undefined}
              className={styles.link}
            >
              {SECTION_LABEL[sectionId]}
            </a>
          </li>
        ))}
      </ol>
    </nav>
  )
}
