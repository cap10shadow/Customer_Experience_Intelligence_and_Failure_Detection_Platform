import { useMemo, useRef } from 'react'
import { useLocation } from 'react-router-dom'

import { useOptionalDatasetContext } from '@/app/context/DatasetContext'
import { useDisclosure } from '@/shared/hooks/useDisclosure'

import { deriveWorkspaceContext } from '../context/deriveWorkspaceContext'
import { useCopilotConversation } from '../hooks/useCopilotConversation'
import { CopilotLauncher } from './CopilotLauncher'
import { CopilotPanel } from './CopilotPanel'

/**
 * The single Copilot mount point (architecture §4/§32) -- rendered once
 * inside `AppShell`, as a sibling of the routed `<Outlet/>`, never
 * duplicated per-workspace. Survives workspace navigation: the panel's
 * open/closed state and the active conversation both live in this one
 * instance, so switching workspaces via the Sidebar never resets an
 * open conversation.
 *
 * `POST /copilot/messages` is operator-level at the Gateway (main.py's
 * `_require_operator`), so a `viewer` could previously open the panel,
 * type a question, send it, and receive only a `403` -- the restriction
 * was discoverable solely by failing. `canUseCopilot` is now passed in
 * from `AppShell` (the one component already reading `AuthContext`) so
 * the panel can state it before the first message instead. Visibility is
 * still not the authorization boundary; the launcher and panel remain
 * available and the Gateway remains authoritative.
 */
export interface CopilotProps {
  /** Whether this session holds the `operator` role Copilot requires. Defaults to `true` so a standalone render keeps the pre-existing behaviour rather than showing a spurious restriction. */
  canUseCopilot?: boolean
}

export function Copilot({ canUseCopilot = true }: CopilotProps = {}) {
  const location = useLocation()
  const { isOpen, close, toggle } = useDisclosure()
  const launcherRef = useRef<HTMLButtonElement>(null)
  const { messages, isLoading, error, sendMessage, retry } = useCopilotConversation()

  // `DatasetContext` is mounted in `AppProviders`, outside the router, a
  // sibling of `AuthProvider` -- unlike the per-workspace contexts
  // `deriveWorkspaceContext.ts` deliberately doesn't reach for, this one is
  // real app-wide state reachable here without prop-drilling or a new
  // duplicate context (same reachability `canUseCopilot` already relies on
  // for `AuthContext`). `useOptionalDatasetContext` (not the throwing
  // variant) keeps this component renderable standalone in tests.
  const datasetContext = useOptionalDatasetContext()
  const selectedDatasetId = datasetContext?.selectedDatasetId ?? null

  const workspaceContext = useMemo(() => {
    const base = deriveWorkspaceContext(location.pathname)
    if (!selectedDatasetId) return base
    return { ...base, filters: { ...base.filters, datasetId: selectedDatasetId } }
  }, [location.pathname, selectedDatasetId])

  return (
    <>
      <CopilotLauncher ref={launcherRef} isOpen={isOpen} onClick={toggle} />
      {isOpen ? (
        <CopilotPanel
          workspace={workspaceContext.workspace}
          canUseCopilot={canUseCopilot}
          messages={messages}
          isLoading={isLoading}
          error={error}
          onSend={(text) => sendMessage(text, workspaceContext)}
          onRetry={retry}
          onClose={close}
          launcherRef={launcherRef}
        />
      ) : null}
    </>
  )
}
