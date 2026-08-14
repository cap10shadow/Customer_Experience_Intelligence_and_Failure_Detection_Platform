import { useRef } from 'react'
import { useLocation } from 'react-router-dom'

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
 */
export function Copilot() {
  const location = useLocation()
  const { isOpen, close, toggle } = useDisclosure()
  const launcherRef = useRef<HTMLButtonElement>(null)
  const { messages, isLoading, error, sendMessage, retry } = useCopilotConversation()

  const workspaceContext = deriveWorkspaceContext(location.pathname)

  return (
    <>
      <CopilotLauncher ref={launcherRef} isOpen={isOpen} onClick={toggle} />
      {isOpen ? (
        <CopilotPanel
          workspace={workspaceContext.workspace}
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
