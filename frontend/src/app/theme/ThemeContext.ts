import { createContext } from 'react'

/** `system` defers to the OS/browser's `prefers-color-scheme`; `light`/`dark` are explicit overrides. */
export type ThemeMode = 'light' | 'dark' | 'system'
export type ResolvedTheme = 'light' | 'dark'

export interface ThemeContextValue {
  /** The user's stored preference -- may be 'system'. */
  mode: ThemeMode
  /** The theme actually applied right now (system resolved to light/dark). */
  resolvedTheme: ResolvedTheme
  setMode: (mode: ThemeMode) => void
}

export const ThemeContext = createContext<ThemeContextValue | undefined>(undefined)
