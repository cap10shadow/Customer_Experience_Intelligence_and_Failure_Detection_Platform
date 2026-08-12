import { Component, type ErrorInfo, type ReactNode } from 'react'

import { Icon } from '@/shared/icons'

import styles from './ErrorBoundary.module.css'

export interface ErrorBoundaryProps {
  children: ReactNode
  /** What failed, in user terms (e.g. "the Recommendations queue") -- used in the fallback's heading so the failure is legible, not a stack trace. */
  boundaryLabel: string
  onError?: (error: Error, info: ErrorInfo) => void
  /**
   * Called when the user selects "Try again," before this boundary clears
   * its own caught error -- pass a workspace data hook's `refetch` so a
   * retry genuinely issues a new request, not merely a remount that
   * re-renders the same already-failed state (Part 7 rectification: this
   * was previously a known limitation across Dashboard/Investigation/
   * Recommendation/Analytics). Optional so non-data-backed boundaries
   * (e.g. sections with no fetch to retry) don't need to supply one --
   * they still get a working "reset this boundary" retry.
   */
  onRetry?: () => void
  /**
   * When any entry in this array differs (shallow, by index) from its
   * previous render, an already-caught error clears automatically -- the
   * same `resetKeys` convention the `react-error-boundary` library
   * popularized (not that package; this is our own minimal version of it).
   *
   * Exists for the case `onRetry` alone doesn't cover: several sibling
   * ErrorBoundaries fed by the *same* data hook (e.g. Dashboard's three
   * data-backed sections). Clicking "Try again" in just one of them
   * re-triggers the one shared fetch, but without this, the *other*
   * siblings' own caught-error state never clears even after that fetch
   * succeeds -- each has its own independent `state.error`, and nothing
   * else tells it the underlying data actually changed. Passing the
   * hook's own `[isLoading]` (or `[data]`/`[error]`) as `resetKeys` means
   * every sibling observes the same transition and recovers together.
   */
  resetKeys?: readonly unknown[]
}

interface ErrorBoundaryState {
  error: Error | null
}

/**
 * React error boundaries must be class components -- this is the one
 * foundation component in the whole architecture that cannot be a
 * function component, by React's own design. Every workspace route
 * (see AppRouter) is wrapped in one of these so a failure in one
 * workspace can never blank the entire application shell.
 */
export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { error: null }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    this.props.onError?.(error, info)
  }

  componentDidUpdate(prevProps: ErrorBoundaryProps) {
    if (!this.state.error) {
      return
    }
    const previousKeys = prevProps.resetKeys
    const nextKeys = this.props.resetKeys
    if (!nextKeys || nextKeys.length !== previousKeys?.length) {
      return
    }
    const changed = nextKeys.some((key, index) => key !== previousKeys[index])
    if (changed) {
      this.setState({ error: null })
    }
  }

  private handleRetry = () => {
    this.props.onRetry?.()
    this.setState({ error: null })
  }

  render() {
    const { error } = this.state
    const { children, boundaryLabel } = this.props

    if (!error) {
      return children
    }

    return (
      <div role="alert" className={styles.container}>
        <Icon name="warning" size={28} className={styles.icon} />
        <div>
          <p className={styles.title}>Something went wrong loading {boundaryLabel}</p>
          <p className={styles.message}>{error.message || 'An unexpected error occurred.'}</p>
        </div>
        <button type="button" className={styles.retryButton} onClick={this.handleRetry}>
          Try again
        </button>
      </div>
    )
  }
}
