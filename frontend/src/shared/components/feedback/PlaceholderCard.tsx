import { classNames } from '@/shared/utilities/classNames'

import styles from './PlaceholderCard.module.css'

export interface PlaceholderCardProps {
  /** What will eventually live here (e.g. "Complaint spike summary widget") -- this is an architectural marker, not user-facing copy for a shipped feature. */
  title: string
  description?: string
  className?: string
}

/**
 * Marks where a future business widget will be implemented, without
 * implementing it -- exactly what Phase 10 Step 1 calls for ("establish
 * only the architectural structure... do NOT implement final widgets").
 * Visually distinct (dashed border) so it reads as scaffolding, not a
 * finished empty state.
 */
export function PlaceholderCard({ title, description, className }: PlaceholderCardProps) {
  return (
    <div className={classNames(styles.card, className)}>
      <p className={styles.title}>{title}</p>
      {description ? <p className={styles.description}>{description}</p> : null}
    </div>
  )
}
