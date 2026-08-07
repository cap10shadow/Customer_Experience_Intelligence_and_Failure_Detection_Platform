import { ANALYTICS_SECTION_ORDER, useAnalyticsContext, type AnalyticsSectionId } from '../../context'
import { ScopeIndicator } from './ScopeIndicator'
import styles from './AnalyticsNavigator.module.css'

const SECTION_LABEL: Record<AnalyticsSectionId, string> = {
  'executive-overview': 'Executive Overview',
  'trend-analysis': 'Trend Analysis',
  'pattern-discovery': 'Pattern Discovery',
  'recommendation-effectiveness': 'Recommendation Effectiveness',
  'organizational-insights': 'Organizational Insights',
  'strategic-opportunities': 'Strategic Opportunities',
}

/**
 * UX-009: the persistent, always-visible map of Analytics, structurally
 * mirroring `InvestigationNavigator`/`RecommendationNavigator` exactly
 * -- real fragment links, `aria-current` on click, no scroll-spy, same
 * navigator family, not a new paradigm. Carries UX-005's shared Scope
 * Indicator the same way `RecommendationNavigator` carries its
 * persistent Decision reference -- one calm, informational block, never
 * a control.
 */
export function AnalyticsNavigator() {
  const { activeSection, setActiveSection } = useAnalyticsContext()

  return (
    <nav aria-label="Analytics sections" className={styles.navigator}>
      <ol className={styles.list}>
        {ANALYTICS_SECTION_ORDER.map((sectionId) => (
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
      <div className={styles.scopeSlot}>
        <ScopeIndicator />
      </div>
    </nav>
  )
}
