import { StatusIndicator } from '@/shared/components/utility'

import { RECOMMENDATION_SECTION_ORDER, useRecommendationContext, type RecommendationSectionId } from '../../context'
import { DECISION_STATUS_LABEL, DECISION_STATUS_TONE, type DecisionRecord } from '../../types'
import styles from './RecommendationNavigator.module.css'

const SECTION_LABEL: Record<RecommendationSectionId, string> = {
  overview: 'Recommendation Overview',
  rationale: 'Recommendation Rationale',
  'alternative-options': 'Alternative Options',
  'expected-outcome': 'Expected Outcome',
  'risk-assessment': 'Risk Assessment',
  decision: 'Decision',
  lifecycle: 'Recommendation Lifecycle',
}

export interface RecommendationNavigatorProps {
  decision: DecisionRecord
}

/**
 * The persistent, always-visible map of the recommendation, structurally
 * mirroring `InvestigationNavigator` exactly (UX-004: reuse Investigation
 * Workspace navigation, do not invent another model) -- real fragment
 * links, `aria-current` on click, no scroll-spy. Also carries UX-001's
 * persistent Decision reference: a single calm status line, not a call
 * to action. Never a colored "alarm" tone even for 'rejected' -- a past
 * decision is informational, not a warning to act on.
 */
export function RecommendationNavigator({ decision }: RecommendationNavigatorProps) {
  const { activeSection, setActiveSection } = useRecommendationContext()

  return (
    <nav aria-label="Recommendation sections" className={styles.navigator}>
      <ol className={styles.list}>
        {RECOMMENDATION_SECTION_ORDER.map((sectionId) => (
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
      <div className={styles.decisionReference}>
        <span className={styles.decisionReferenceLabel}>Current status</span>
        <StatusIndicator tone={DECISION_STATUS_TONE[decision.status]} label={DECISION_STATUS_LABEL[decision.status]} />
      </div>
    </nav>
  )
}
