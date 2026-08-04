import type { ReactNode } from 'react'

import { classNames } from '@/shared/utilities/classNames'

import styles from './LoadingContainer.module.css'

export interface LoadingContainerProps {
  isLoading: boolean
  /** Announced to screen readers while loading (e.g. "Loading operational brief"). Keep specific -- "Loading" alone is not useful when a page has several async regions. */
  label: string
  /** The resolved content, shown once `isLoading` is false. Omit entirely when this is used purely as a `<Suspense>` fallback (isLoading is always true in that case, so children are never reached). */
  children?: ReactNode
  className?: string
}

/**
 * The one place `aria-busy`/`aria-live` loading semantics are implemented
 * -- every future async region (a workspace fetching real data) wraps its
 * content in this rather than each hand-rolling a spinner and loading
 * announcement. Also doubles as a `Suspense` fallback (see WorkspaceLayout)
 * since a route-chunk download is just another form of loading state.
 */
export function LoadingContainer({ isLoading, label, children, className }: LoadingContainerProps) {
  return (
    <div className={classNames(styles.container, className)} aria-busy={isLoading} aria-live="polite">
      {isLoading ? (
        <div className={styles.spinnerWrapper}>
          <span className={styles.spinner} aria-hidden="true" />
          <span className="visually-hidden">{label}</span>
        </div>
      ) : (
        children
      )}
    </div>
  )
}
