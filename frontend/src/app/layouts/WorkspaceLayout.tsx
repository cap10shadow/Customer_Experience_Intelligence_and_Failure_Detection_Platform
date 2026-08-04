import { Suspense, type ReactNode } from 'react'

import { ErrorBoundary, LoadingContainer, PageTransition } from '@/shared/components/feedback'

export interface WorkspaceLayoutProps {
  children: ReactNode
}

/**
 * Wraps the active workspace route's content with the three cross-cutting
 * concerns every workspace needs, so no individual workspace has to
 * reimplement them:
 *  - `Suspense` -- the route-level code-splitting boundary (workspaces are
 *    lazy-loaded, see AppRouter); shows a loading state while the
 *    workspace's JS chunk downloads.
 *  - `ErrorBoundary` -- an error in one workspace can never blank the
 *    persistent Sidebar/TopBar or crash the whole app.
 *  - `PageTransition` -- the calm fade used on every workspace change.
 */
export function WorkspaceLayout({ children }: WorkspaceLayoutProps) {
  return (
    <ErrorBoundary boundaryLabel="this workspace">
      <Suspense fallback={<LoadingContainer isLoading label="Loading workspace" />}>
        <PageTransition>{children}</PageTransition>
      </Suspense>
    </ErrorBoundary>
  )
}
