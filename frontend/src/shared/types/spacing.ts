/** Keys into foundations.css's `--space-*` scale -- the only spacing values layout primitives accept, so arbitrary pixel values never leak into component code. */
export type SpaceScale = 0 | 1 | 2 | 3 | 4 | 5 | 6 | 8 | 10 | 12 | 16

export function spaceVar(token: SpaceScale): string {
  return `var(--space-${token})`
}
