import { Link, isRouteErrorResponse, useRouteError } from 'react-router-dom'

import { EmptyState } from '@/shared/components/feedback'

import { ROUTE_PATHS } from './routePaths'
import styles from './RouteErrorView.module.css'

/**
 * The router's own failure surface -- what a user sees for a URL that
 * matches no route, or for an error thrown by the router itself before
 * any workspace mounts. Without it, react-router falls back to its raw
 * "Unexpected Application Error!" developer screen, which is neither
 * honest nor recoverable for an operator.
 *
 * Deliberately built from the existing `EmptyState` foundation rather
 * than a new UI primitive: an unreachable URL is a legitimate outcome to
 * state plainly, with exactly one way forward (back to the Dashboard).
 */
export interface RouteErrorViewProps {
  /**
   * `not-found` is asserted by the catch-all route, which knows by
   * construction that the URL matched nothing -- there is no error to
   * inspect in that case. Omitted when mounted as `errorElement`, where
   * the thrown value decides.
   */
  variant?: 'not-found'
}

export function RouteErrorView({ variant }: RouteErrorViewProps = {}) {
  const error = useRouteError()
  const isNotFound = variant === 'not-found' || (isRouteErrorResponse(error) && error.status === 404)

  const title = isNotFound ? 'This page does not exist' : 'This page could not be opened'
  const description = isNotFound
    ? 'The address you followed does not match anything in the platform. It may be out of date, or the record it pointed to may no longer exist.'
    : 'Something went wrong before this page could load. Returning to the Dashboard is the reliable way forward.'

  return (
    <EmptyState
      icon={isNotFound ? 'info' : 'warning'}
      title={title}
      description={description}
      action={
        <Link to={ROUTE_PATHS.dashboard} className={styles.homeLink}>
          Back to Dashboard
        </Link>
      }
    />
  )
}
