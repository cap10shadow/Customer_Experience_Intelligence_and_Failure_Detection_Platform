import { classNames } from '@/shared/utilities/classNames'

import styles from './Logo.module.css'

export interface LogoProps {
  /** Hides the wordmark, showing only the mark -- used in the collapsed sidebar state. */
  compact?: boolean
  className?: string
}

/**
 * A neutral placeholder mark, not a finished brand asset -- "do not
 * finalize branding" is honored by keeping this a simple, token-driven
 * monogram rather than a designed logotype. Swapping in real brand
 * assets later touches only this one component.
 */
export function Logo({ compact = false, className }: LogoProps) {
  return (
    <span className={classNames(styles.logo, className)}>
      <span className={styles.mark} aria-hidden="true">
        OI
      </span>
      {compact ? null : <span className={styles.wordmark}>Operational Intelligence</span>}
    </span>
  )
}
