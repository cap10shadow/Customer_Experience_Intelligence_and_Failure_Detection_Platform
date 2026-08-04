import type { ReactNode } from 'react'

import { Icon, type IconName } from '@/shared/icons'
import { classNames } from '@/shared/utilities/classNames'

import styles from './EmptyState.module.css'

export interface EmptyStateProps {
  icon?: IconName
  title: string
  description?: string
  /** A single primary action slot (e.g. a future "Start an investigation" link) -- never more than one, to keep the empty state calm rather than a decision point. */
  action?: ReactNode
  className?: string
}

/**
 * The deliberate alternative to silently rendering nothing. "Never
 * present information simply because it exists" cuts both ways -- an
 * empty result is still a result, and the user needs to know that
 * clearly rather than wonder whether something failed to load.
 */
export function EmptyState({ icon = 'info', title, description, action, className }: EmptyStateProps) {
  return (
    <div className={classNames(styles.container, className)}>
      <Icon name={icon} size={32} className={styles.icon} />
      <p className={styles.title}>{title}</p>
      {description ? <p className={styles.description}>{description}</p> : null}
      {action ? <div className={styles.actions}>{action}</div> : null}
    </div>
  )
}
