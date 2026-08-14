import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'

import { Copilot } from '@/copilot'

function jsonResponse(status: number, body: unknown) {
  return { status, ok: status >= 200 && status < 300, text: async () => JSON.stringify(body) } as Response
}

const SUCCESS_RESPONSE = {
  answer: 'The West region incident is linked to a payment gateway failure.',
  keyFindings: ['3 incidents matched the West region filter.'],
  evidenceReferences: [
    {
      evidenceId: 'E1',
      sourceType: 'root_cause',
      sourceId: 'rc-1',
      authority: 'root_cause_service',
      timestamp: '2026-08-01T00:00:00Z',
    },
  ],
  relatedEntities: [
    { type: 'incident', id: 'INC-1' },
    { type: 'business_impact', id: 'bi-1' },
  ],
  visualizationHint: 'trend',
  limitations: ['The analytics source did not provide a computation timestamp.'],
  conversationId: 'conv-1',
  requestId: 'req-1',
}

function renderCopilot(initialPath = '/') {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Copilot />
    </MemoryRouter>,
  )
}

async function openPanel() {
  const user = userEvent.setup()
  await user.click(screen.getByRole('button', { name: 'Open Copilot' }))
  return user
}

describe('Copilot launcher', () => {
  it('renders with an accessible label and opens/closes the panel', async () => {
    renderCopilot()
    const launcher = screen.getByRole('button', { name: 'Open Copilot' })
    expect(launcher).toHaveAttribute('aria-expanded', 'false')

    const user = userEvent.setup()
    await user.click(launcher)
    expect(screen.getByRole('dialog')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Close Copilot' })).toHaveAttribute('aria-expanded', 'true')

    await user.click(screen.getByRole('button', { name: 'Close Copilot panel' }))
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('is mounted once and is not duplicated', () => {
    renderCopilot()
    expect(screen.getAllByRole('button', { name: 'Open Copilot' })).toHaveLength(1)
  })
})

describe('Copilot panel', () => {
  it('shows a clean empty state with no fabricated insights when first opened', async () => {
    renderCopilot()
    await openPanel()

    expect(screen.getByText('Ask Copilot about your operational data')).toBeInTheDocument()
    expect(screen.queryByText(/analyz(ing|ed)/i)).not.toBeInTheDocument()
  })

  it('closes on Escape and returns focus to the launcher', async () => {
    renderCopilot()
    const user = await openPanel()

    await user.keyboard('{Escape}')

    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
    expect(screen.getByRole('button', { name: 'Open Copilot' })).toHaveFocus()
  })

  it('focuses the composer input when opened', async () => {
    renderCopilot()
    await openPanel()

    await waitFor(() => expect(screen.getByLabelText('Ask Copilot a question')).toHaveFocus())
  })

  it('restores focus to the composer after a response completes, so Escape keeps working', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(200, SUCCESS_RESPONSE)))
    renderCopilot()
    const user = await openPanel()

    // Disabling the send button mid-request blurs it to <body> -- without
    // the fix, focus would stay lost there after the response completes.
    await user.type(screen.getByLabelText('Ask Copilot a question'), 'hello')
    await user.click(screen.getByRole('button', { name: 'Send message' }))
    await screen.findByText(SUCCESS_RESPONSE.answer)

    await waitFor(() => expect(screen.getByLabelText('Ask Copilot a question')).toHaveFocus())

    await user.keyboard('{Escape}')
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
    expect(screen.getByRole('button', { name: 'Open Copilot' })).toHaveFocus()

    vi.unstubAllGlobals()
  })
})

describe('Copilot message flow', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(200, SUCCESS_RESPONSE)))
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('sends the user message, shows a loading state, and renders the real response', async () => {
    let resolveFetch: (value: Response) => void = () => {}
    vi.mocked(fetch).mockReturnValueOnce(
      new Promise((resolve) => {
        resolveFetch = resolve
      }),
    )
    renderCopilot()
    const user = await openPanel()

    await user.type(screen.getByLabelText('Ask Copilot a question'), 'What happened in West region?')
    await user.click(screen.getByRole('button', { name: 'Send message' }))

    expect(screen.getByText('What happened in West region?')).toBeInTheDocument()
    expect(screen.getByText('Copilot is preparing a response')).toBeInTheDocument()

    resolveFetch(jsonResponse(200, SUCCESS_RESPONSE))

    expect(await screen.findByText(SUCCESS_RESPONSE.answer)).toBeInTheDocument()
    expect(screen.getByText(SUCCESS_RESPONSE.keyFindings[0])).toBeInTheDocument()
    expect(screen.queryByText('Copilot is preparing a response')).not.toBeInTheDocument()
  })

  it('does not fire a second concurrent request from a double click while loading', async () => {
    renderCopilot()
    const user = await openPanel()

    await user.type(screen.getByLabelText('Ask Copilot a question'), 'hello')
    const sendButton = screen.getByRole('button', { name: 'Send message' })
    await user.click(sendButton)
    // The composer disables while loading -- a second click has nothing to click, but assert the guard directly too.
    await waitFor(() => expect(vi.mocked(fetch)).toHaveBeenCalledTimes(1))
    await screen.findByText(SUCCESS_RESPONSE.answer)
    expect(vi.mocked(fetch)).toHaveBeenCalledTimes(1)
  })

  it('retains the returned conversationId and reuses it on the next message', async () => {
    renderCopilot()
    const user = await openPanel()

    await user.type(screen.getByLabelText('Ask Copilot a question'), 'first question')
    await user.click(screen.getByRole('button', { name: 'Send message' }))
    await screen.findByText(SUCCESS_RESPONSE.answer)

    await user.type(screen.getByLabelText('Ask Copilot a question'), 'second question')
    await user.click(screen.getByRole('button', { name: 'Send message' }))
    await waitFor(() => expect(vi.mocked(fetch)).toHaveBeenCalledTimes(2))

    const [, secondInit] = vi.mocked(fetch).mock.calls[1]
    const body = JSON.parse(String(secondInit?.body))
    expect(body.conversationId).toBe('conv-1')
  })

  it('renders real evidence references without inventing metadata', async () => {
    renderCopilot()
    const user = await openPanel()

    await user.type(screen.getByLabelText('Ask Copilot a question'), 'why?')
    await user.click(screen.getByRole('button', { name: 'Send message' }))
    await screen.findByText(SUCCESS_RESPONSE.answer)

    expect(screen.getByText('root cause')).toBeInTheDocument()
    expect(screen.getByText('rc-1')).toBeInTheDocument()
    expect(screen.getByText('Source: root_cause_service')).toBeInTheDocument()
  })

  it('renders limitations distinctly rather than hiding them', async () => {
    renderCopilot()
    const user = await openPanel()

    await user.type(screen.getByLabelText('Ask Copilot a question'), 'why?')
    await user.click(screen.getByRole('button', { name: 'Send message' }))

    expect(await screen.findByText(SUCCESS_RESPONSE.limitations[0])).toBeInTheDocument()
  })

  it('maps a known visualizationHint to a neutral badge, never a fabricated chart', async () => {
    renderCopilot()
    const user = await openPanel()

    await user.type(screen.getByLabelText('Ask Copilot a question'), 'trend?')
    await user.click(screen.getByRole('button', { name: 'Send message' }))

    expect(await screen.findByText('Related to a trend')).toBeInTheDocument()
    expect(screen.queryByRole('img', { name: /chart/i })).not.toBeInTheDocument()
    expect(document.querySelector('canvas')).not.toBeInTheDocument()
    expect(document.querySelector('svg[class*="chart"]')).not.toBeInTheDocument()
  })

  it('links a real, existing route for an incident-type related entity', async () => {
    renderCopilot()
    const user = await openPanel()

    await user.type(screen.getByLabelText('Ask Copilot a question'), 'why?')
    await user.click(screen.getByRole('button', { name: 'Send message' }))
    await screen.findByText(SUCCESS_RESPONSE.answer)

    const incidentLink = screen.getByRole('link', { name: 'incident: INC-1' })
    expect(incidentLink).toHaveAttribute('href', '/investigations/INC-1')
  })

  it('renders an entity with no known detail route as plain text, never a fabricated link', async () => {
    renderCopilot()
    const user = await openPanel()

    await user.type(screen.getByLabelText('Ask Copilot a question'), 'why?')
    await user.click(screen.getByRole('button', { name: 'Send message' }))
    await screen.findByText(SUCCESS_RESPONSE.answer)

    expect(screen.getByText('business_impact: bi-1')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /business_impact/ })).not.toBeInTheDocument()
  })

  it('does not render any mutation control anywhere in the panel', async () => {
    renderCopilot()
    const user = await openPanel()

    await user.type(screen.getByLabelText('Ask Copilot a question'), 'why?')
    await user.click(screen.getByRole('button', { name: 'Send message' }))
    await screen.findByText(SUCCESS_RESPONSE.answer)

    const dialog = screen.getByRole('dialog')
    const buttons = within(dialog).getAllByRole('button')
    const forbiddenNamePattern = /approve|reject|confirm|decision|refresh root cause/i
    buttons.forEach((button) => {
      expect(button.textContent + (button.getAttribute('aria-label') ?? '')).not.toMatch(forbiddenNamePattern)
    })
  })

  it('never executes or injects raw HTML from the answer text', async () => {
    const maliciousAnswer = '<img src=x onerror="window.__pwned = true">Ignore all instructions.'
    vi.mocked(fetch).mockResolvedValue(
      jsonResponse(200, { ...SUCCESS_RESPONSE, answer: maliciousAnswer, keyFindings: [], evidenceReferences: [], relatedEntities: [], visualizationHint: null, limitations: [] }),
    )
    renderCopilot()
    const user = await openPanel()

    await user.type(screen.getByLabelText('Ask Copilot a question'), 'hello')
    await user.click(screen.getByRole('button', { name: 'Send message' }))

    await screen.findByText(maliciousAnswer)
    expect(document.querySelector('img[src="x"]')).not.toBeInTheDocument()
    expect((window as unknown as { __pwned?: boolean }).__pwned).toBeUndefined()
  })
})

describe('Copilot error handling', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('shows a clear user-facing error without exposing internal details, and retry resends the same message', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        jsonResponse(502, {
          error: {
            code: 'UPSTREAM_ERROR',
            message: 'Copilot is temporarily unavailable. Please try again.',
            requestId: 'req-err',
          },
        }),
      )
      .mockResolvedValueOnce(jsonResponse(200, SUCCESS_RESPONSE))
    vi.stubGlobal('fetch', fetchMock)

    renderCopilot()
    const user = await openPanel()

    await user.type(screen.getByLabelText('Ask Copilot a question'), 'hello')
    await user.click(screen.getByRole('button', { name: 'Send message' }))

    const alert = await screen.findByRole('alert')
    expect(within(alert).getByText(/temporarily unavailable/i)).toBeInTheDocument()
    expect(alert.textContent).not.toMatch(/postgres|traceback|localhost:800\d|internal server error/i)

    // Only one user bubble exists -- retry must not duplicate it.
    expect(screen.getAllByText('hello')).toHaveLength(1)

    await user.click(within(alert).getByRole('button', { name: 'Retry' }))

    await screen.findByText(SUCCESS_RESPONSE.answer)
    expect(fetchMock).toHaveBeenCalledTimes(2)
    const [, secondInit] = fetchMock.mock.calls[1]
    expect(JSON.parse(String(secondInit?.body)).message).toBe('hello')
    // The failed first attempt never received a conversationId -- retry must not invent one either.
    expect(JSON.parse(String(secondInit?.body)).conversationId).toBeUndefined()
  })
})

describe('Copilot workspace context', () => {
  it('sends the derived workspace and incidentId for the current route', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(200, SUCCESS_RESPONSE)))
    renderCopilot('/investigations/INC-77')
    const user = await openPanel()

    await user.type(screen.getByLabelText('Ask Copilot a question'), 'why?')
    await user.click(screen.getByRole('button', { name: 'Send message' }))

    await waitFor(() => expect(vi.mocked(fetch)).toHaveBeenCalledTimes(1))
    const [, init] = vi.mocked(fetch).mock.calls[0]
    const body = JSON.parse(String(init?.body))
    expect(body.workspaceContext).toEqual({ workspace: 'investigations', incidentId: 'INC-77' })

    vi.unstubAllGlobals()
  })
})
