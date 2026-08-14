import { useEffect, useRef } from 'react'

import { EmptyState } from '@/shared/components/feedback'

import type { CopilotTranscriptMessage } from '../hooks/useCopilotConversation'
import { CopilotMessage } from './CopilotMessage'
import styles from './CopilotMessageList.module.css'

export interface CopilotMessageListProps {
  messages: CopilotTranscriptMessage[]
  isLoading: boolean
}

/**
 * The visible transcript. Empty state uses only honest, architecture-
 * approved product language (Batch 5 implementation prompt §16) -- it
 * never claims Copilot has already analyzed the current workspace, and
 * never shows fabricated suggested findings.
 */
export function CopilotMessageList({ messages, isLoading }: CopilotMessageListProps) {
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    // Optional chaining on the call itself, not just the ref: jsdom (this
    // project's test environment) does not implement `scrollIntoView`.
    endRef.current?.scrollIntoView?.({ block: 'end' })
  }, [messages.length, isLoading])

  if (messages.length === 0 && !isLoading) {
    return (
      <div className={styles.list}>
        <EmptyState
          icon="chat"
          title="Ask Copilot about your operational data"
          description="Ask about a specific incident, recommendation, or trend. Copilot answers using real data already in the platform."
        />
      </div>
    )
  }

  return (
    <div className={styles.list} role="log" aria-live="polite" aria-label="Copilot conversation">
      {messages.map((message) => (
        <CopilotMessage key={message.id} message={message} />
      ))}
      {isLoading ? (
        <div className={styles.loadingRow} aria-hidden="false">
          <span className={styles.loadingDot} />
          <span className={styles.loadingDot} />
          <span className={styles.loadingDot} />
          <span className="visually-hidden">Copilot is preparing a response</span>
        </div>
      ) : null}
      <div ref={endRef} />
    </div>
  )
}
