import { useState, type FormEvent } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'

import { ApiError } from '@/app/api/errors'
import { ROUTE_PATHS } from '@/app/routing/routePaths'
import { Logo } from '@/shared/components/utility'

import { useAuth } from '../context/AuthContext'
import styles from './LoginPage.module.css'

const GENERIC_ERROR_MESSAGE = 'Something went wrong. Please try again.'

/**
 * The platform's one login screen (Phase 13 Batch 2). Deliberately
 * minimal -- email, password, submit, and a single generic error
 * message on failure (the Gateway itself never distinguishes
 * unknown-email/wrong-password/inactive-user, so this page can't either
 * -- AD-6 §10). No password-reset, MFA, or SSO affordance: none exist
 * yet (§30 of the frozen architecture).
 */
export function LoginPage() {
  const { status, sessionExpired, login } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  // Already signed in (e.g. a direct visit to /login) -- send straight
  // to the workspace rather than showing a login form there's no reason
  // to fill in again.
  if (status === 'authenticated') {
    return <Navigate to={ROUTE_PATHS.dashboard} replace />
  }

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setError(null)
    setIsSubmitting(true)

    try {
      await login({ email, password })
      navigate(ROUTE_PATHS.dashboard, { replace: true })
    } catch (cause) {
      if (cause instanceof ApiError && cause.status === 401) {
        setError('Invalid email or password.')
      } else {
        setError(GENERIC_ERROR_MESSAGE)
      }
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className={styles.page}>
      <div className={styles.card}>
        <div className={styles.heading}>
          <Logo />
          <span className={styles.title}>Sign in</span>
          <span className={styles.subtitle}>Enter your credentials to access the platform.</span>
        </div>

        {/* Shown only when a real session ended mid-use (AuthContext's
            `sessionExpired`), never for a first visit or a deliberate
            sign-out -- so a user who was working and got sent back here
            knows why, instead of assuming the application broke. */}
        {sessionExpired ? (
          <p className={styles.notice} role="status">
            Your session ended, so you were signed out. Sign in again to continue where you left off.
          </p>
        ) : null}

        <form className={styles.form} onSubmit={handleSubmit} noValidate>
          <div className={styles.field}>
            <label className={styles.label} htmlFor="login-email">
              Email
            </label>
            <input
              id="login-email"
              className={styles.input}
              type="email"
              autoComplete="username"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
          </div>

          <div className={styles.field}>
            <label className={styles.label} htmlFor="login-password">
              Password
            </label>
            <input
              id="login-password"
              className={styles.input}
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </div>

          {error ? (
            <span className={styles.error} role="alert">
              {error}
            </span>
          ) : null}

          <button className={styles.submit} type="submit" disabled={isSubmitting}>
            {isSubmitting ? 'Signing in…' : 'Sign in'}
          </button>
        </form>
      </div>
    </div>
  )
}
