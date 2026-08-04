import type { ReactNode } from 'react'

/**
 * Icon Registry
 * -------------
 * A small, dependency-free set of neutral, functional line icons (no
 * external icon library) -- deliberately generic shapes, not a finished
 * visual identity. Every icon is drawn on a 24x24 grid so they share one
 * `viewBox` and scale uniformly via `Icon`/`IconWrapper`.
 *
 * Add new icons here only when a foundation component genuinely needs
 * one -- this registry is not a general-purpose icon library.
 */
export const ICONS = {
  dashboard: (
    <>
      <rect x="3" y="3" width="8" height="8" rx="1.5" />
      <rect x="13" y="3" width="8" height="5" rx="1.5" />
      <rect x="13" y="10" width="8" height="11" rx="1.5" />
      <rect x="3" y="13" width="8" height="8" rx="1.5" />
    </>
  ),
  actionCenter: (
    <>
      <path d="M12 3v9l4 2" />
      <circle cx="12" cy="12" r="9" />
    </>
  ),
  investigations: (
    <>
      <circle cx="10.5" cy="10.5" r="6.5" />
      <path d="m20 20-4.35-4.35" />
    </>
  ),
  recommendations: (
    <>
      <path d="M9 18h6" />
      <path d="M10 21h4" />
      <path d="M12 3a6 6 0 0 0-3.6 10.8c.5.4.8 1 .9 1.7h5.4c.1-.7.4-1.3.9-1.7A6 6 0 0 0 12 3Z" />
    </>
  ),
  analytics: (
    <>
      <path d="M4 20V10" />
      <path d="M11 20V4" />
      <path d="M18 20v-7" />
      <path d="M3 20h18" />
    </>
  ),
  administration: (
    <>
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 13.5c.05-.5.05-1 0-1.5l1.9-1.5-2-3.4-2.3.9a7.8 7.8 0 0 0-1.3-.75L15.3 5h-4l-.4 2.25c-.47.2-.9.45-1.3.75l-2.3-.9-2 3.4L7.1 12c-.05.5-.05 1 0 1.5l-1.9 1.5 2 3.4 2.3-.9c.4.3.83.55 1.3.75L11.3 21h4l.4-2.25c.47-.2.9-.45 1.3-.75l2.3.9 2-3.4z" />
    </>
  ),
  menu: (
    <>
      <path d="M3 6h18" />
      <path d="M3 12h18" />
      <path d="M3 18h18" />
    </>
  ),
  chevronDown: <path d="m6 9 6 6 6-6" />,
  chevronRight: <path d="m9 6 6 6-6 6" />,
  bell: (
    <>
      <path d="M18 16v-5a6 6 0 0 0-12 0v5l-1.5 2.5h15z" />
      <path d="M10.5 21a1.5 1.5 0 0 0 3 0" />
    </>
  ),
  search: (
    <>
      <circle cx="11" cy="11" r="7" />
      <path d="m20 20-3.5-3.5" />
    </>
  ),
  user: (
    <>
      <circle cx="12" cy="8" r="3.5" />
      <path d="M4.5 20a7.5 7.5 0 0 1 15 0" />
    </>
  ),
  close: (
    <>
      <path d="m5 5 14 14" />
      <path d="m19 5-14 14" />
    </>
  ),
  warning: (
    <>
      <path d="M12 3 2 20h20L12 3Z" />
      <path d="M12 10v4" />
      <path d="M12 17h.01" />
    </>
  ),
  info: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 11v5" />
      <path d="M12 8h.01" />
    </>
  ),
  check: <path d="m4 12 6 6L20 6" />,
  alertCircle: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 8v4" />
      <path d="M12 16h.01" />
    </>
  ),
  home: (
    <>
      <path d="M4 11.5 12 4l8 7.5" />
      <path d="M6 10v10h12V10" />
    </>
  ),
} satisfies Record<string, ReactNode>

export type IconName = keyof typeof ICONS
