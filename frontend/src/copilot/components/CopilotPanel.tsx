import { useEffect, useRef, type KeyboardEvent, type RefObject } from 'react'

import { Icon } from '@/shared/icons'
import { Panel } from '@/shared/components/layout'

import type { ApiError } from '@/app/api/errors'
import type { CopilotTranscriptMessage } from '../hooks/useCopilotConversation'
import type { CopilotWorkspaceName } from '../api/types'
import { CopilotMessageList } from './CopilotMessageList'
import { CopilotComposer } from './CopilotComposer'
import styles from './CopilotPanel.module.css'

const WORKSPACE_LABEL: Record<CopilotWorkspaceName, string> = {
  dashboard: 'Dashboard',
  investigations: 'Investigations',
  recommendations: 'Recommendations',
  analytics: 'Analytics',
  administration: 'Administration',
}

function friendlyErrorMessage(error: ApiError): string {
  if (error.status === 0) {
    return 'Copilot could not reach the platform. Check your connection and try again.'
  }
  if (error.status >= 500) {
    return 'Copilot is temporarily unavailable. Please try again.'
  }
  return error.message || 'Something went wrong answering that question.'
}

export interface CopilotPanelProps {
  workspace: CopilotWorkspaceName
  messages: CopilotTranscriptMessage[]
  isLoading: boolean
  error: ApiError | null
  onSend: (text: string) => void
  onRetry: () => void
  onClose: () => void
  launcherRef: RefObject<HTMLButtonElement | null>
}

/**
 * The compact, expandable, non-full-screen panel (architecture §4/§32).
 * Closes on Escape (focus returns to the launcher, mirroring `UserMenu`'s
 * established pattern) and traps Tab focus within the panel while open
 * (§32: "Panel focus trapping while expanded (without blocking the rest
 * of the page from being read/scrolled)") -- deliberately does *not*
 * close on outside click, unlike `UserMenu`: the whole point of this
 * panel (§4, "usable while the workspace remains visible") is that the
 * user can keep interacting with the workspace behind it while a
 * conversation stays open.
 */
export function CopilotPanel({
  workspace,
  messages,
  isLoading,
  error,
  onSend,
  onRetry,
  onClose,
  launcherRef,
}: CopilotPanelProps) {
  const panelRef = useRef<HTMLDivElement>(null)
  const wasLoadingRef = useRef(false)

  useEffect(() => {
    const input = panelRef.current?.querySelector<HTMLElement>('#copilot-composer-input')
    input?.focus()
  }, [])

  useEffect(() => {
    // The composer's send button is disabled while `isLoading` (§20's
    // duplicate-submission guard) -- disabling a focused element blurs it
    // to `<body>` in every browser, which would otherwise silently break
    // Escape/keyboard interaction (`<body>` is outside this panel's own
    // `onKeyDown` subtree) for the rest of the session once a response
    // completes. Restore focus to the composer input the moment a request
    // finishes, exactly where a user would expect to keep typing anyway.
    if (wasLoadingRef.current && !isLoading) {
      panelRef.current?.querySelector<HTMLElement>('#copilot-composer-input')?.focus()
    }
    wasLoadingRef.current = isLoading
  }, [isLoading])

  const handleKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key === 'Escape') {
      onClose()
      launcherRef.current?.focus()
      return
    }
    if (event.key !== 'Tab') return

    const focusable = panelRef.current?.querySelectorAll<HTMLElement>(
      'button:not(:disabled), textarea:not(:disabled), a[href]',
    )
    if (!focusable || focusable.length === 0) return
    const first = focusable[0]
    const last = focusable[focusable.length - 1]

    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault()
      last.focus()
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault()
      first.focus()
    }
  }

  return (
    <div
      ref={panelRef}
      role="dialog"
      aria-modal="false"
      aria-labelledby="copilot-panel-heading"
      className={styles.panelWrapper}
      onKeyDown={handleKeyDown}
    >
      <Panel elevated padded={false} className={styles.panel}>
        <header className={styles.header}>
          <div>
            <h2 id="copilot-panel-heading" className={styles.heading}>
              Copilot
            </h2>
            <p className={styles.subheading}>{WORKSPACE_LABEL[workspace]}</p>
          </div>
          <button type="button" className={styles.closeButton} onClick={onClose} aria-label="Close Copilot panel">
            <Icon name="close" size={18} />
          </button>
        </header>

        <CopilotMessageList messages={messages} isLoading={isLoading} />

        {error ? (
          <div role="alert" className={styles.errorBanner}>
            <p>{friendlyErrorMessage(error)}</p>
            <button type="button" className={styles.retryButton} onClick={onRetry}>
              Retry
            </button>
          </div>
        ) : null}

        <CopilotComposer isLoading={isLoading} onSend={onSend} />
      </Panel>
    </div>
  )
}
