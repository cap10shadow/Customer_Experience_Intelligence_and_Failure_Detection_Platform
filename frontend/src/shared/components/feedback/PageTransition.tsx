import type { ReactNode } from 'react'

import { classNames } from '@/shared/utilities/classNames'

import styles from './PageTransition.module.css'

export interface PageTransitionProps {
  children: ReactNode
  className?: string
}

/**
 * A calm, subtle fade-in used at the workspace route boundary (see
 * AppRouter) -- collapses to an instant, motionless swap under
 * `prefers-reduced-motion` automatically, since it animates via the
 * `--motion-duration-slow` token rather than a hard-coded duration.
 */
export function PageTransition({ children, className }: PageTransitionProps) {
  return <div className={classNames(styles.transition, className)}>{children}</div>
}
