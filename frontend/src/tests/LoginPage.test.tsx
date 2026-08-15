import { afterEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'

import { LoginPage } from '@/auth/components/LoginPage'
import { AuthProvider } from '@/auth/context/AuthContext'

function jsonResponse(body: unknown, status = 200) {
  return { status, ok: status >= 200 && status < 300, text: async () => JSON.stringify(body) } as Response
}

function renderLoginPage() {
  return render(
    <MemoryRouter initialEntries={['/login']}>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/" element={<div>Dashboard screen</div>} />
        </Routes>
      </AuthProvider>
    </MemoryRouter>,
  )
}

describe('LoginPage', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('renders email and password fields and a submit button', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(jsonResponse({ error: { code: 'UNAUTHENTICATED', message: 'x', requestId: 'r' } }, 401)),
    )

    renderLoginPage()

    await waitFor(() => expect(screen.getByLabelText('Email')).toBeInTheDocument())
    expect(screen.getByLabelText('Password')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Sign in' })).toBeInTheDocument()
  })

  it('shows a generic error and stays on the login screen for invalid credentials', async () => {
    const user = userEvent.setup()
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation((_url: string, options?: RequestInit) => {
        if (options?.method === 'POST') {
          return Promise.resolve(
            jsonResponse({ error: { code: 'UNAUTHENTICATED', message: 'Invalid email or password.', requestId: 'r' } }, 401),
          )
        }
        return Promise.resolve(jsonResponse({ error: { code: 'UNAUTHENTICATED', message: 'x', requestId: 'r' } }, 401))
      }),
    )

    renderLoginPage()
    await waitFor(() => expect(screen.getByLabelText('Email')).toBeInTheDocument())

    await user.type(screen.getByLabelText('Email'), 'alice@example.com')
    await user.type(screen.getByLabelText('Password'), 'wrong-password')
    await user.click(screen.getByRole('button', { name: 'Sign in' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Invalid email or password.')
    expect(screen.queryByText('Dashboard screen')).not.toBeInTheDocument()
  })

  it('navigates to the dashboard after a successful login', async () => {
    const user = userEvent.setup()
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation((_url: string, options?: RequestInit) => {
        if (options?.method === 'POST') {
          return Promise.resolve(jsonResponse({ userId: 'u1', email: 'alice@example.com', roles: [] }))
        }
        return Promise.resolve(jsonResponse({ error: { code: 'UNAUTHENTICATED', message: 'x', requestId: 'r' } }, 401))
      }),
    )

    renderLoginPage()
    await waitFor(() => expect(screen.getByLabelText('Email')).toBeInTheDocument())

    await user.type(screen.getByLabelText('Email'), 'alice@example.com')
    await user.type(screen.getByLabelText('Password'), 'correct-password')
    await user.click(screen.getByRole('button', { name: 'Sign in' }))

    expect(await screen.findByText('Dashboard screen')).toBeInTheDocument()
  })

  it('redirects away from /login immediately when already authenticated', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse({ userId: 'u1', email: 'alice@example.com', roles: [] })))

    renderLoginPage()

    expect(await screen.findByText('Dashboard screen')).toBeInTheDocument()
  })
})
