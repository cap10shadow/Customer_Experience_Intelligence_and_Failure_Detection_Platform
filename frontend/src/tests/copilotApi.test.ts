import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { postCopilotMessage } from '@/copilot/api/copilotApi'

function jsonResponse(body: unknown) {
  return { status: 200, ok: true, text: async () => JSON.stringify(body) } as Response
}

describe('copilotApi.postCopilotMessage', () => {
  beforeEach(() => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        jsonResponse({
          answer: 'ok',
          keyFindings: [],
          evidenceReferences: [],
          relatedEntities: [],
          visualizationHint: null,
          limitations: [],
          conversationId: 'conv-1',
          requestId: 'req-1',
        }),
      ),
    )
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('posts to the real, prefixed Gateway Copilot route', async () => {
    await postCopilotMessage({ message: 'hello' })

    const [requestedUrl, init] = vi.mocked(fetch).mock.calls[0]
    const url = new URL(String(requestedUrl))
    // `toContain`, not exact equality, matching `recommendationApi.test.ts`'s
    // own convention -- robust to whatever `env.apiBaseUrl` prefix this
    // test process resolves (unset here, so it takes the '/api' default;
    // the real docker deployment's `VITE_API_BASE_URL` differs -- see
    // copilotApi.ts's own docstring and the Batch 5 report).
    expect(url.pathname).toContain('/api/v1/copilot/messages')
    expect(init?.method).toBe('POST')
  })

  it('sends message, conversationId, and workspaceContext exactly as given, never inventing a client-side conversation id', async () => {
    await postCopilotMessage({
      message: 'why?',
      conversationId: 'conv-42',
      workspaceContext: { workspace: 'investigations', incidentId: 'INC-1' },
    })

    const [, init] = vi.mocked(fetch).mock.calls[0]
    const body = JSON.parse(String(init?.body))
    expect(body).toEqual({
      message: 'why?',
      conversationId: 'conv-42',
      workspaceContext: { workspace: 'investigations', incidentId: 'INC-1' },
    })
  })

  it('omits conversationId when absent, rather than sending a fabricated one', async () => {
    await postCopilotMessage({ message: 'hello' })

    const [, init] = vi.mocked(fetch).mock.calls[0]
    const body = JSON.parse(String(init?.body))
    expect(body.conversationId).toBeUndefined()
  })

  it('resolves to the parsed CopilotResponse body', async () => {
    const response = await postCopilotMessage({ message: 'hello' })
    expect(response.conversationId).toBe('conv-1')
    expect(response.requestId).toBe('req-1')
  })
})
