import type { ReactNode } from 'react'

import { classNames } from '@/shared/utilities/classNames'
import { Panel } from '@/shared/components/layout'

import styles from './Card.module.css'

export interface CardProps {
  /** Card title -- omit for a card with only custom `children` content. */
  title?: ReactNode
  /** Rendered next to the title (e.g. a status Badge) -- see AdministrationSection's Live/Not Yet Operational usage. */
  titleAccessory?: ReactNode
  description?: ReactNode
  children?: ReactNode
  /** Rendered in a footer row, visually separated from the body (e.g. actions). */
  footer?: ReactNode
  className?: string
}

/**
 * A generic titled surface built on `Panel` (the platform's existing base
 * surface primitive) rather than reinventing background/border/radius --
 * this only adds the title/description/footer slots that ~15 hand-rolled
 * workspace card components (ConnectedSystemCard, FactCard, EvidenceCard,
 * etc.) each redefine independently. Adopted by new work (Data/Ingestion,
 * Administration's retrofit) going forward; existing workspace-specific
 * cards are left as-is for this pass (see docs/PROJECT_STATUS.md's
 * design-system gap note) rather than migrated wholesale.
 */
export function Card({ title, titleAccessory, description, children, footer, className }: CardProps) {
  const hasHeader = title !== undefined || description !== undefined

  return (
    <Panel className={classNames(styles.card, className)}>
      {hasHeader ? (
        <header className={styles.header}>
          {title !== undefined ? (
            <div className={styles.titleRow}>
              <h3 className={styles.title}>{title}</h3>
              {titleAccessory}
            </div>
          ) : null}
          {description !== undefined ? <p className={styles.description}>{description}</p> : null}
        </header>
      ) : null}
      {children ? <div className={styles.body}>{children}</div> : null}
      {footer ? <footer className={styles.footer}>{footer}</footer> : null}
    </Panel>
  )
}
