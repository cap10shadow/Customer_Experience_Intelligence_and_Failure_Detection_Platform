import { BREAKPOINTS, MEDIA_QUERIES, type BreakpointKey } from '@/shared/constants/breakpoints'

import { useMediaQuery } from './useMediaQuery'

/** True once the viewport is at least as wide as the given named breakpoint. */
export function useBreakpoint(breakpoint: BreakpointKey): boolean {
  return useMediaQuery(MEDIA_QUERIES[breakpoint])
}

/** The single largest breakpoint the current viewport satisfies -- convenient for layout branching that needs one value, not a set of booleans. */
export function useActiveBreakpoint(): BreakpointKey {
  const isSm = useBreakpoint('sm')
  const isMd = useBreakpoint('md')
  const isLg = useBreakpoint('lg')
  const isXl = useBreakpoint('xl')

  if (isXl) return 'xl'
  if (isLg) return 'lg'
  if (isMd) return 'md'
  if (isSm) return 'sm'
  return 'xs'
}

export { BREAKPOINTS }
