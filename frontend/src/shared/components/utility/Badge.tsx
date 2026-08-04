import type { ReactNode } from 'react'

import { classNames } from '@/shared/utilities/classNames'

import styles from './Badge.module.css'

export type BadgeTone = 'neutral' | 'critical' | 'warning' | 'success' | 'info' | 'accent'

export interface BadgeProps {
  children: ReactNode
  tone?: BadgeTone
  className?: string
}

/**
 * A small labeled chip -- counts, categories, short tags. Unlike
 * `StatusIndicator`, a Badge's text *is* the content (not a
 * screen-reader-only fallback), so it is not itself a color-only signal;
 * still prefer pairing with a visible word ("3 new", not just "3" in a
 * status color) wherever the count alone could be ambiguous.
 */
export function Badge({ children, tone = 'neutral', className }: BadgeProps) {
  return <span className={classNames(styles.badge, styles[tone], className)}>{children}</span>
}
