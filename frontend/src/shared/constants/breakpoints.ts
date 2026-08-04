/**
 * Breakpoint scale -- the single source of truth for responsive behavior.
 * CSS custom properties cannot be interpolated into a `@media` query, so
 * these pixel values are authoritative; component CSS Modules hard-code
 * matching `@media` rules by convention, and JS-side responsive logic
 * (useBreakpoint/useMediaQuery) reads these constants directly, so the two
 * never drift silently.
 *
 * Desktop (`xl`) is the primary operational experience; smaller
 * breakpoints reorganize information, they never remove operational
 * capability (see product-experience-guide).
 */
export const BREAKPOINTS = {
  xs: 0, // mobile
  sm: 640, // large mobile / small tablet
  md: 1024, // tablet / small laptop
  lg: 1280, // laptop
  xl: 1536, // desktop
} as const

export type BreakpointKey = keyof typeof BREAKPOINTS

export const MEDIA_QUERIES: Record<BreakpointKey, string> = {
  xs: `(min-width: ${BREAKPOINTS.xs}px)`,
  sm: `(min-width: ${BREAKPOINTS.sm}px)`,
  md: `(min-width: ${BREAKPOINTS.md}px)`,
  lg: `(min-width: ${BREAKPOINTS.lg}px)`,
  xl: `(min-width: ${BREAKPOINTS.xl}px)`,
}
