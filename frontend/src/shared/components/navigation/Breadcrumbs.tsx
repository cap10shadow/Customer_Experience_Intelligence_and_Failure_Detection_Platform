import { Link } from 'react-router-dom'

import type { BreadcrumbSegment } from '@/shared/types/navigation'
import { Icon } from '@/shared/icons'

import styles from './Breadcrumbs.module.css'

export interface BreadcrumbsProps {
  segments: BreadcrumbSegment[]
}

/**
 * Foundation only, per the frozen navigation architecture ("breadcrumb
 * foundation", not deep hierarchical trails yet) -- workspaces pass a
 * flat list of segments today (typically just their own name); a future
 * Investigations drill-down path (Complaint -> Incident -> ...) extends
 * this same component with more segments, unchanged.
 */
export function Breadcrumbs({ segments }: BreadcrumbsProps) {
  if (segments.length === 0) return null

  return (
    <nav aria-label="Breadcrumb">
      <ol className={styles.list}>
        {segments.map((segment, index) => {
          const isLast = index === segments.length - 1
          return (
            <li key={`${segment.label}-${index}`} className={styles.item}>
              {index > 0 ? (
                <span className={styles.separator} aria-hidden="true">
                  <Icon name="chevronRight" size={14} />
                </span>
              ) : null}
              {segment.path && !isLast ? (
                <Link to={segment.path} className={styles.link}>
                  {segment.label}
                </Link>
              ) : (
                <span className={styles.current} aria-current={isLast ? 'page' : undefined}>
                  {segment.label}
                </span>
              )}
            </li>
          )
        })}
      </ol>
    </nav>
  )
}
