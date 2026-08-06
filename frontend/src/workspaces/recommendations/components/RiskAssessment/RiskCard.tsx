import { RecommendationLoadingState } from '../foundation'
import type { RiskItem } from '../../types'
import styles from './RiskCard.module.css'

export interface RiskCardProps {
  risk: RiskItem
  isLoading?: boolean
}

/**
 * UX-002: distinct grouping and spacing, deliberately never warning
 * styling, stronger colors, or alarm visuals -- risk is communicated
 * through typography and whitespace (Calm Software), the same way
 * every other section is, not through red borders or caution icons.
 */
export function RiskCard({ risk, isLoading = false }: RiskCardProps) {
  if (isLoading) {
    return (
      <div className={styles.item}>
        <RecommendationLoadingState label="Loading risk" />
      </div>
    )
  }

  return (
    <div className={styles.item}>
      <p className={styles.headline}>{risk.headline}</p>
      <p className={styles.detail}>{risk.detail}</p>
    </div>
  )
}
