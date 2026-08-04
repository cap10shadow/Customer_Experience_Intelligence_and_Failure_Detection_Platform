import { useContext } from 'react'

import { ThemeContext, type ThemeContextValue } from './ThemeContext'

/** Reads the current theme mode/resolved theme and lets callers change it. Must be used within `ThemeProvider`. */
export function useTheme(): ThemeContextValue {
  const context = useContext(ThemeContext)
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider')
  }
  return context
}
