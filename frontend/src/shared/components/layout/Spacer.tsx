import type { SpaceScale } from '@/shared/types/spacing'
import { spaceVar } from '@/shared/types/spacing'

export interface SpacerProps {
  size: SpaceScale
  axis?: 'horizontal' | 'vertical'
}

/** An explicit, token-driven gap for the rare case a flex/grid `gap` isn't the right tool (e.g. spacing between two inline elements without wrapping them in a Stack). */
export function Spacer({ size, axis = 'vertical' }: SpacerProps) {
  const dimension = spaceVar(size)
  return (
    <span
      aria-hidden="true"
      style={{
        display: 'block',
        width: axis === 'horizontal' ? dimension : undefined,
        height: axis === 'vertical' ? dimension : undefined,
        flexShrink: 0,
      }}
    />
  )
}
