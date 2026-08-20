import type { ReactNode } from 'react'

import { Icon, type IconName } from '@/shared/icons'

import styles from './AdvisoryNotice.module.css'

export interface AdvisoryNoticeProps {
  /** A short statement of what is true -- e.g. "Illustrative content" or "Recording a decision requires the operator role". */
  title: string
  /** One or two sentences of supporting detail. Always factual; never speculative and never an apology. */
  description: string
  icon?: IconName
  /** An optional recovery action -- e.g. a "Retry" button when the notice describes a failed fetch. */
  action?: ReactNode
}

/**
 * A calm, non-blocking statement of fact *about* the content beside it --
 * distinct from every existing feedback component:
 *
 * - `ErrorBoundary`  -- this section failed to load.
 * - `EmptyState`     -- the platform computes this, and there is nothing.
 * - `FutureCapabilityPlaceholder` -- the platform does not compute this yet.
 * - `PartialFailureNotice` -- part of an otherwise-successful response
 *   was unavailable.
 * - `AdvisoryNotice` (this) -- the content shown *is* here and *is*
 *   rendering, but the reader needs one honest fact to interpret it
 *   correctly: that it is illustrative rather than live, or that acting
 *   on it requires a role this session does not hold.
 *
 * Introduced because two independent honesty gaps needed exactly the
 * same surface (Administration's presentation-only sections, and the
 * role-gated write actions), so it is one shared component rather than
 * two near-identical local ones.
 */
export function AdvisoryNotice({ title, description, icon = 'info', action }: AdvisoryNoticeProps) {
  return (
    <div role="note" className={styles.container}>
      <Icon name={icon} size={18} className={styles.icon} />
      <div className={styles.body}>
        <p className={styles.title}>{title}</p>
        <p className={styles.description}>{description}</p>
        {action ? <div className={styles.action}>{action}</div> : null}
      </div>
    </div>
  )
}
