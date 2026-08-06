import { RecommendationSection } from '../foundation'
import type { RiskItem } from '../../types'
import { RiskCard } from './RiskCard'
import styles from './RiskAssessment.module.css'

const RISKS: RiskItem[] = [
  { id: 'trade-offs', headline: 'Trade-offs', detail: 'Time spent reviewing the provider change is time not spent on other open work.' },
  { id: 'uncertainty', headline: 'Uncertainty', detail: 'The provider change is the most likely cause, not a confirmed one.' },
  { id: 'implementation-risk', headline: 'Implementation risk', detail: 'If the cause is different than expected, the review may not resolve the issue.' },
  { id: 'business-risk', headline: 'Business risk', detail: 'Checkout failures continue at the current rate while this is reviewed.' },
]

export interface RiskAssessmentProps {
  isLoading?: boolean
}

/**
 * UX-002: a distinct grouping, distinct spacing, and a distinct
 * container from every other section -- but never warning styling,
 * stronger colors, or alarm visuals. The `.container` below is the one
 * place in this workspace with its own visual treatment (a quieter
 * background, more generous internal spacing), and it is intentionally
 * still neutral: same text colors, same typography scale as everywhere
 * else.
 */
export function RiskAssessment({ isLoading = false }: RiskAssessmentProps) {
  return (
    <RecommendationSection id="risk-assessment" title="Risk Assessment" description="What could go wrong?">
      <div className={styles.container}>
        {RISKS.map((risk) => (
          <RiskCard key={risk.id} risk={risk} isLoading={isLoading} />
        ))}
      </div>
    </RecommendationSection>
  )
}
