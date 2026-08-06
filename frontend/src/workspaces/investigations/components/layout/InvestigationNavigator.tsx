import { INVESTIGATION_SECTION_ORDER, useInvestigationContext, type InvestigationSectionId } from '../../context'
import styles from './InvestigationNavigator.module.css'

const SECTION_LABEL: Record<InvestigationSectionId, string> = {
  observation: 'Observation',
  evidence: 'Evidence',
  'root-cause': 'Root Cause Analysis',
  'business-impact': 'Business Impact',
  'recommended-next-step': 'Recommended Next Step',
}

/**
 * The persistent, always-visible map of the investigation -- real
 * fragment links (keyboard- and screen-reader-navigable, work with
 * browser back/forward, functional with JavaScript disabled), not a
 * JS-only scroll-spy. `aria-current` reflects `activeSection`, which
 * updates on click; no scroll detection is implemented -- this is a
 * structured document a user can jump around in, not a guided tour, so
 * "where am I" only needs to answer "where did I last navigate to."
 */
export function InvestigationNavigator() {
  const { activeSection, setActiveSection } = useInvestigationContext()

  return (
    <nav aria-label="Investigation sections" className={styles.navigator}>
      <ol className={styles.list}>
        {INVESTIGATION_SECTION_ORDER.map((sectionId) => (
          <li key={sectionId}>
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
