import { Component, type ErrorInfo, type ReactNode } from 'react'

import { Icon } from '@/shared/icons'

import styles from './ErrorBoundary.module.css'

export interface ErrorBoundaryProps {
  children: ReactNode
  /** What failed, in user terms (e.g. "the Action Center queue") -- used in the fallback's heading so the failure is legible, not a stack trace. */
  boundaryLabel: string
  onError?: (error: Error, info: ErrorInfo) => void
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

  private handleRetry = () => {
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
