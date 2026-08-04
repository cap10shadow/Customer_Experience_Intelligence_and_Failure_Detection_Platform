import type { ReactNode } from 'react'

import { classNames } from '@/shared/utilities/classNames'

import styles from './SidebarSection.module.css'

export interface SidebarSectionProps {
  /** Visible section heading (e.g. a future "Pinned"). Omit for the primary, unlabeled workspace list. */
  title?: string
  children: ReactNode
  className?: string
}

/** One vertical block of the sidebar -- the primary navigation is one section today; future sections (recents, pinned items) stack below it without any Sidebar changes. */
export function SidebarSection({ title, children, className }: SidebarSectionProps) {
  return (
    <div className={classNames(styles.section, className)}>
      {title ? <p className={styles.heading}>{title}</p> : null}
      {children}
    </div>
  )
}
