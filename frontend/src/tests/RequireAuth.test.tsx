import { afterEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'

import { RequireAuth } from '@/auth/components/RequireAuth'
import { AuthProvider } from '@/auth/context/AuthContext'

function jsonResponse(body: unknown, status = 200) {
  return { status, ok: status >= 200 && status < 300, text: async () => JSON.stringify(body) } as Response
}

function renderAt(initialPath: string) {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<div>Login screen</div>} />
          <Route
            path="/"
            element={
              <RequireAuth>
                <div>Protected content</div>
              </RequireAuth>
            }
          />
        </Routes>
      </AuthProvider>
    </MemoryRouter>,
  )
}

describe('RequireAuth', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('shows a checking state before the session bootstrap resolves', () => {
    vi.stubGlobal('fetch', vi.fn(() => new Promise(() => {})))

    renderAt('/')

    expect(screen.getByText('Checking your session')).toBeInTheDocument()
  })

  it('redirects to /login when the session is unauthenticated', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(jsonResponse({ error: { code: 'UNAUTHENTICATED', message: 'x', requestId: 'r' } }, 401)),
    )

    renderAt('/')

    await waitFor(() => expect(screen.getByText('Login screen')).toBeInTheDocument())
    expect(screen.queryByText('Protected content')).not.toBeInTheDocument()
  })

  it('renders the protected content once a real session is confirmed', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse({ userId: 'u1', email: 'a@example.com', roles: [] })))

    renderAt('/')

    await waitFor(() => expect(screen.getByText('Protected content')).toBeInTheDocument())
  })
})
