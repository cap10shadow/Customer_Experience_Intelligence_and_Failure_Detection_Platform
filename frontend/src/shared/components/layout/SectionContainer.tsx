import { useId, type ReactNode } from 'react'

import { classNames } from '@/shared/utilities/classNames'

import styles from './SectionContainer.module.css'

export interface SectionContainerProps {
  /** Section title -- rendered as a real heading and used to label the `<section>` landmark for assistive tech. */
  title: string
  description?: string
  /** Heading level for this section's title, so callers can keep the document's heading hierarchy correct (e.g. h2 under a WorkspaceHeader's h1). Defaults to h2, the level every workspace's top-level sections should use. */
  headingLevel?: 2 | 3 | 4
  /** Supporting actions aligned to the section header (e.g. a future "View all" link) -- never business logic, just a slot. */
  actions?: ReactNode
  children: ReactNode
  className?: string
}

/**
 * The architectural unit every workspace section (Operational Brief,
 * Decision Summary, a future Action Center queue, ...) is built from: a
 * labelled `<section>` landmark with a real, correctly-leveled heading.
 * This is what "proper heading hierarchy" and "accessible landmarks"
 * mean in practice at the component level.
 */
export function SectionContainer({
  title,
  description,
  headingLevel = 2,
  actions,
  children,
  className,
}: SectionContainerProps) {
  const headingId = useId()
  const HeadingTag = `h${headingLevel}` as const

  return (
    <section aria-labelledby={headingId} className={classNames(styles.section, className)}>
      <div className={styles.header}>
        <div>
          <HeadingTag id={headingId} className={styles.heading}>
            {title}
          </HeadingTag>
          {description ? <p className={styles.description}>{description}</p> : null}
        </div>
        {actions ? <div className={styles.actions}>{actions}</div> : null}
      </div>
      {children}
    </section>
  )
}
