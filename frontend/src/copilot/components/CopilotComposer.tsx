import { useState, type FormEvent, type KeyboardEvent } from 'react'

import { Icon } from '@/shared/icons'

import styles from './CopilotComposer.module.css'

export interface CopilotComposerProps {
  isLoading: boolean
  onSend: (text: string) => void
}

/**
 * The message input. Disabled while a request is in flight (Batch 5
 * implementation prompt §20) so a second click/Enter cannot fire a
 * concurrent request -- paired with `useCopilotConversation`'s own
 * `isLoading` guard as defense in depth.
 */
export function CopilotComposer({ isLoading, onSend }: CopilotComposerProps) {
  const [draft, setDraft] = useState('')

  const submit = () => {
    const trimmed = draft.trim()
    if (!trimmed || isLoading) return
    onSend(trimmed)
    setDraft('')
  }

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault()
    submit()
  }

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      submit()
    }
  }

  return (
    <form className={styles.composer} onSubmit={handleSubmit}>
      <label htmlFor="copilot-composer-input" className="visually-hidden">
        Ask Copilot a question
      </label>
      <textarea
        id="copilot-composer-input"
        className={styles.input}
        placeholder="Ask about an incident, recommendation, or trend..."
        rows={1}
        value={draft}
        disabled={isLoading}
        onChange={(event) => setDraft(event.target.value)}
        onKeyDown={handleKeyDown}
      />
      <button type="submit" className={styles.sendButton} disabled={isLoading || !draft.trim()} aria-label="Send message">
        <Icon name="send" size={18} />
      </button>
    </form>
  )
}
