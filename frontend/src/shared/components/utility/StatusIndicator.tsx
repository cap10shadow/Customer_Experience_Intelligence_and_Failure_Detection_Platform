import type { IconName } from '@/shared/icons'
import { Icon } from '@/shared/icons'
import { classNames } from '@/shared/utilities/classNames'

import styles from './StatusIndicator.module.css'

export type StatusTone = 'critical' | 'warning' | 'success' | 'info' | 'neutral'

const TONE_ICON: Record<StatusTone, IconName> = {
  critical: 'alertCircle',
  warning: 'warning',
  success: 'check',
  info: 'info',
  neutral: 'info',
}

export interface StatusIndicatorProps {
  tone: StatusTone
  /** Always required, even when visually hidden -- status must never be conveyed by color alone (color-independent interaction states). */
  label: string
  /** Hides the visible text, keeping it for assistive tech only -- use in dense contexts (e.g. a table cell) where the icon shape alone is legible next to other context. */
  visuallyHideLabel?: boolean
  className?: string
}

/**
 * Communicates operational status via a distinct icon *shape* per tone,
 * not color alone -- a color-blind or grayscale-display user can still
 * distinguish critical (!) from success (check) from info (i). Color
 * reinforces the shape; it never stands alone.
 */
export function StatusIndicator({ tone, label, visuallyHideLabel = false, className }: StatusIndicatorProps) {
  return (
    <span className={classNames(styles.indicator, styles[tone], className)}>
      <Icon name={TONE_ICON[tone]} size={16} />
      <span className={classNames(styles.label, visuallyHideLabel && 'visually-hidden')}>{label}</span>
    </span>
  )
}
