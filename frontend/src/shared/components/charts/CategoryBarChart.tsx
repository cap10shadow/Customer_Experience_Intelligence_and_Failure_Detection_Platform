import { classNames } from '@/shared/utilities/classNames'

import styles from './CategoryBarChart.module.css'

/** Reserved operational tones. Omit entirely unless the category genuinely *is* a status -- see the CSS note. */
export type CategoryBarTone = 'critical' | 'warning' | 'info' | 'neutral'

export interface CategoryBarItem {
  label: string
  value: number
  tone?: CategoryBarTone
}

export interface CategoryBarChartProps {
  items: CategoryBarItem[]
  /** Describes the whole plot for a screen reader, e.g. "Complaint count by category". */
  ariaLabel: string
}

const TONE_CLASS: Record<CategoryBarTone, string> = {
  critical: styles.toneCritical,
  warning: styles.toneWarning,
  info: styles.toneInfo,
  neutral: styles.toneNeutral,
}

/**
 * Horizontal bars comparing a magnitude across named categories.
 *
 * Bars are scaled against the largest value in the set, and the scale
 * always starts at zero -- a truncated baseline would misrepresent the
 * ratio between two counts, which is the only thing this form exists to
 * show. Items are rendered in exactly the order supplied; this component
 * never sorts, never aggregates a long tail into "Other", and never
 * derives a percentage the caller didn't pass.
 */
export function CategoryBarChart({ items, ariaLabel }: CategoryBarChartProps) {
  if (items.length === 0) {
    return null
  }

  const largest = Math.max(...items.map((item) => item.value))

  return (
    <ul className={styles.list} aria-label={ariaLabel}>
      {items.map((item) => (
        <li key={item.label} className={styles.row}>
          <p className={styles.label}>{item.label}</p>
          <div className={styles.track}>
            <div
              className={classNames(styles.bar, item.tone ? TONE_CLASS[item.tone] : undefined)}
              // Percentage width, so the bar tracks the container at any
              // viewport size without measurement.
              style={{ width: `${largest > 0 ? (item.value / largest) * 100 : 0}%` }}
            />
          </div>
          <p className={styles.value}>{item.value.toLocaleString()}</p>
        </li>
      ))}
    </ul>
  )
}
