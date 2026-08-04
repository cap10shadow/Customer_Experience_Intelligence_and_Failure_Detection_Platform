import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'

import { ThemeContext, type ResolvedTheme, type ThemeMode } from './ThemeContext'

const STORAGE_KEY = 'oi-platform:theme-mode'

function readStoredMode(): ThemeMode {
  if (typeof window === 'undefined') return 'system'
  const stored = window.localStorage.getItem(STORAGE_KEY)
  return stored === 'light' || stored === 'dark' || stored === 'system' ? stored : 'system'
}

function getSystemTheme(): ResolvedTheme {
  if (typeof window === 'undefined' || !window.matchMedia) return 'light'
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

/**
 * Theme Provider (architectural foundation only)
 *
 * Establishes light/dark/system theme resolution and organization-branding
 * extension points required by this phase, without exposing any visible
 * theme-switching UI -- none was requested. `mode` defaults to and
 * persists as 'system', so out of the box every user simply sees their
 * OS preference via tokens.css's `prefers-color-scheme` block; this
 * provider's job is purely to make an explicit override *possible* later
 * (a future settings screen only ever needs to call `setMode`).
 *
 * Sets `data-theme` on `<html>` only when the mode is explicit ('light' or
 * 'dark'); in 'system' mode no attribute is set, so tokens.css's
 * `@media (prefers-color-scheme)` block is what actually applies --
 * `:root[data-theme]` and the media query never fight over precedence.
 */
export function ThemeProvider({ children }: { children: ReactNode }) {
  const [mode, setModeState] = useState<ThemeMode>(readStoredMode)
  const [systemTheme, setSystemTheme] = useState<ResolvedTheme>(getSystemTheme)

  useEffect(() => {
    if (typeof window === 'undefined' || !window.matchMedia) return
    const query = window.matchMedia('(prefers-color-scheme: dark)')
    const handleChange = (event: MediaQueryListEvent) => {
      setSystemTheme(event.matches ? 'dark' : 'light')
    }
    query.addEventListener('change', handleChange)
    return () => query.removeEventListener('change', handleChange)
  }, [])

  const resolvedTheme: ResolvedTheme = mode === 'system' ? systemTheme : mode

  useEffect(() => {
    const root = document.documentElement
    if (mode === 'system') {
      delete root.dataset.theme
    } else {
      root.dataset.theme = mode
    }
  }, [mode])

  const setMode = useCallback((next: ThemeMode) => {
    setModeState(next)
    window.localStorage.setItem(STORAGE_KEY, next)
  }, [])

  const value = useMemo(() => ({ mode, resolvedTheme, setMode }), [mode, resolvedTheme, setMode])

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
}
