import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'

import { ApiError, describeApiError } from '@/app/api/errors'
import { CopilotPanel } from '@/copilot/components/CopilotPanel'
import { Decision } from '@/workspaces/recommendations/components/Decision'

/**
 * The platform's two role-gated write actions are `PATCH
 * /recommendations/{id}/decision` (operator) and `POST
 * /copilot/messages` (operator). Both previously rendered an identical,
 * fully-enabled control for a `viewer`, who could only discover the
 * restriction by composing a request and receiving a `403`.
 *
 * These tests assert the honest middle ground the frozen architecture
 * requires: the control is never hidden (frontend visibility is not
 * authorization -- the Gateway stays the boundary), but the restriction
 * is stated before the user invests effort in an action that cannot
 * succeed.
 */
describe('role-aware UX for the two operator-gated actions', () => {
  it('tells a read-only session that recording a decision needs the operator role, without hiding the form', () => {
    render(
      <MemoryRouter>
        <Decision canRecordDecision={false} onSubmitDecision={() => {}} />
      </MemoryRouter>,
    )

    expect(screen.getByText('Recording a decision requires the operator role')).toBeInTheDocument()
    // Still rendered: the backend is the authorization boundary, and
    // hiding the control would misrepresent why it is unavailable.
    expect(screen.getByRole('button', { name: 'Save decision' })).toBeInTheDocument()
  })

  it('shows no role notice for a session that does hold the operator role', () => {
    render(
      <MemoryRouter>
        <Decision canRecordDecision onSubmitDecision={() => {}} />
      </MemoryRouter>,
    )

    expect(screen.queryByText('Recording a decision requires the operator role')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Save decision' })).toBeInTheDocument()
  })

  it('tells a read-only session that Copilot needs the operator role, without hiding the composer', () => {
    render(
      <CopilotPanel
        workspace="dashboard"
        canUseCopilot={false}
        messages={[]}
        isLoading={false}
        error={null}
        onSend={() => {}}
        onRetry={() => {}}
        onClose={() => {}}
        launcherRef={{ current: null }}
      />,
    )

    expect(screen.getByText('Asking Copilot requires the operator role')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /send/i })).toBeInTheDocument()
  })

  it('shows no Copilot role notice for an operator session', () => {
    render(
      <CopilotPanel
        workspace="dashboard"
        canUseCopilot
        messages={[]}
        isLoading={false}
        error={null}
        onSend={() => {}}
        onRetry={() => {}}
        onClose={() => {}}
        launcherRef={{ current: null }}
      />,
    )

    expect(screen.queryByText('Asking Copilot requires the operator role')).not.toBeInTheDocument()
  })
})

/**
 * One shared status→sentence mapping, so a `403` never again reaches a
 * user as a bare "Not authorized" that omits the actual reason, and a
 * transport failure never reaches them as a raw exception string.
 */
describe('describeApiError', () => {
  function error(status: number, code = 'X', message = 'raw envelope message') {
    return new ApiError({ code, message, status })
  }

  it('names the user role as the reason for a 403', () => {
    expect(describeApiError(error(403), { subject: 'record this decision' })).toContain('role does not permit')
    expect(describeApiError(error(403), { subject: 'record this decision' })).toContain('record this decision')
  })

  it('explains a 401 as an ended session rather than a failure of the request', () => {
    expect(describeApiError(error(401))).toContain('session has ended')
  })

  it('distinguishes a timeout from an unreachable platform', () => {
    expect(describeApiError(error(0, 'REQUEST_TIMEOUT'))).toContain('took too long')
    expect(describeApiError(error(0, 'NETWORK_ERROR'))).toContain('could not be reached')
  })

  it('states a 404 as a stale address or removed record', () => {
    expect(describeApiError(error(404))).toContain('no longer exists')
  })

  it('keeps the Gateway envelope message for a validation failure, which is already specific', () => {
    expect(describeApiError(error(422, 'VALIDATION_ERROR', 'period must be one of [...]'))).toBe('period must be one of [...]')
  })

  it('never surfaces a raw 5xx envelope, which can carry internal detail', () => {
    const described = describeApiError(error(500, 'INTERNAL', 'Traceback: psycopg.OperationalError'))
    expect(described).not.toContain('Traceback')
    expect(described).toContain('temporarily unavailable')
  })
})
