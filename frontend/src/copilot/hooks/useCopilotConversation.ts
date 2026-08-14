import { useCallback, useRef, useState } from 'react'

import { ApiError } from '@/app/api/errors'

import { postCopilotMessage } from '../api/copilotApi'
import type {
  CopilotEvidenceReference,
  CopilotRelatedEntity,
  CopilotResponse,
  CopilotVisualizationHint,
  CopilotWorkspaceContext,
} from '../api/types'

export interface CopilotUserTranscriptMessage {
  id: string
  role: 'user'
  content: string
}

export interface CopilotAssistantTranscriptMessage {
  id: string
  role: 'assistant'
  content: string
  keyFindings: string[]
  evidenceReferences: CopilotEvidenceReference[]
  relatedEntities: CopilotRelatedEntity[]
  visualizationHint?: CopilotVisualizationHint | null
  limitations: string[]
}

export type CopilotTranscriptMessage = CopilotUserTranscriptMessage | CopilotAssistantTranscriptMessage

function createId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  return `local-${Date.now()}-${Math.random().toString(16).slice(2)}`
}

function toAssistantMessage(response: CopilotResponse): CopilotAssistantTranscriptMessage {
  return {
    id: createId(),
    role: 'assistant',
    content: response.answer,
    keyFindings: response.keyFindings,
    evidenceReferences: response.evidenceReferences,
    relatedEntities: response.relatedEntities,
    visualizationHint: response.visualizationHint,
    limitations: response.limitations,
  }
}

interface PendingRetry {
  text: string
  workspaceContext: CopilotWorkspaceContext | undefined
}

/**
 * Owns the visible current-session Copilot transcript and the active
 * `conversationId` (Batch 4 persistence is authoritative -- this hook
 * never mints its own id; it only retains whatever the backend returns,
 * per architecture §17/Batch 4's "the backend is authoritative"). The
 * backend also persists the real conversation server-side; this hook's
 * `messages` array is only the current browser session's rendered view of
 * it, not a second source of truth.
 *
 * A request in flight (`isLoading`) blocks a second concurrent send
 * (Batch 5 implementation prompt §20) -- both here (defense in depth) and
 * in `CopilotComposer`'s own disabled state.
 */
export function useCopilotConversation() {
  const [messages, setMessages] = useState<CopilotTranscriptMessage[]>([])
  const [conversationId, setConversationId] = useState<string | undefined>(undefined)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<ApiError | null>(null)
  const pendingRetryRef = useRef<PendingRetry | null>(null)
  const conversationIdRef = useRef<string | undefined>(undefined)

  const runRequest = useCallback(async (text: string, workspaceContext: CopilotWorkspaceContext | undefined) => {
    setIsLoading(true)
    setError(null)
    try {
      const response = await postCopilotMessage({
        message: text,
        conversationId: conversationIdRef.current,
        workspaceContext,
      })
      conversationIdRef.current = response.conversationId
      setConversationId(response.conversationId)
      setMessages((previous) => [...previous, toAssistantMessage(response)])
      pendingRetryRef.current = null
    } catch (caught) {
      const apiError =
        caught instanceof ApiError
          ? caught
          : new ApiError({ code: 'UNKNOWN_ERROR', message: 'The request could not be completed.', status: 0 })
      setError(apiError)
      pendingRetryRef.current = { text, workspaceContext }
    } finally {
      setIsLoading(false)
    }
  }, [])

  const sendMessage = useCallback(
    (text: string, workspaceContext: CopilotWorkspaceContext | undefined) => {
      const trimmed = text.trim()
      if (!trimmed || isLoading) return

      const userMessage: CopilotUserTranscriptMessage = { id: createId(), role: 'user', content: trimmed }
      setMessages((previous) => [...previous, userMessage])
      void runRequest(trimmed, workspaceContext)
    },
    [isLoading, runRequest],
  )

  const retry = useCallback(() => {
    const pending = pendingRetryRef.current
    if (!pending || isLoading) return
    void runRequest(pending.text, pending.workspaceContext)
  }, [isLoading, runRequest])

  return { messages, conversationId, isLoading, error, sendMessage, retry }
}
