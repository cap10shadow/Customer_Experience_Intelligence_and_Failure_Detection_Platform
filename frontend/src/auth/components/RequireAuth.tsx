import type { ReactNode } from 'react'
import { Navigate } from 'react-router-dom'

import { ROUTE_PATHS } from '@/app/routing/routePaths'
import { LoadingContainer } from '@/shared/components/feedback'

import { useAuth } from '../context/AuthContext'

export interface RequireAuthProps {
  children: ReactNode
}

/**
 * The frontend-side gate for every workspace route (Phase 13 Batch 2).
 * This is UX convenience only, never the actual security boundary --
 * the Gateway rejects an anonymous request with a real 401 regardless
 * of whether this component ever runs (§12 of the frozen architecture:
 * "frontend visibility is NOT authorization"). Its only job is to avoid
 * flashing protected UI before a session check resolves, and to send a
 * signed-out visitor to `/login` instead of a page full of failed
 * requests.
 */
export function RequireAuth({ children }: RequireAuthProps) {
  const { status } = useAuth()

  if (status === 'checking') {
    return <LoadingContainer isLoading label="Checking your session" />
  }

  if (status !== 'authenticated') {
    return <Navigate to={ROUTE_PATHS.login} replace />
  }

  return children
}
