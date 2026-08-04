import type { ReactNode } from 'react'

import { classNames } from '@/shared/utilities/classNames'

import styles from './PageHeader.module.css'

export interface PageHeaderProps {
  title: string
  description?: string
  headingLevel?: 1 | 2
  actions?: ReactNode
  className?: string
}

/** The generic title/description/actions header block -- WorkspaceHeader is this, fixed to h1, plus document-title management. Kept separate so a future nested page (inside a workspace) can reuse the same visual header at h2 without re-deriving the markup. */
export function PageHeader({ title, description, headingLevel = 1, actions, className }: PageHeaderProps) {
  const HeadingTag = `h${headingLevel}` as const

  return (
    <div className={classNames(styles.header, className)}>
      <div>
        <HeadingTag className={styles.title}>{title}</HeadingTag>
        {description ? <p className={styles.description}>{description}</p> : null}
      </div>
      {actions ? <div className={styles.actions}>{actions}</div> : null}
    </div>
  )
}
