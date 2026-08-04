import type { SVGProps } from 'react'

import { ICONS, type IconName } from './icon-registry'

export interface IconProps extends Omit<SVGProps<SVGSVGElement>, 'name'> {
  name: IconName
  /** Pixel size for both dimensions. Prefer `IconWrapper`'s size tokens over an arbitrary number where possible. */
  size?: number
}

/**
 * Low-level icon renderer. Purely presentational -- carries no
 * accessibility semantics of its own (always `aria-hidden`, since an icon
 * alone never conveys meaning a screen reader should announce). Use
 * `shared/components/utility/IconWrapper` when the icon needs a label
 * (it is the only place `aria-label` for an icon belongs), and use this
 * component directly only from inside other foundation components that
 * already own their own accessible name (e.g. a labelled `<button>`
 * wrapping an icon).
 */
export function Icon({ name, size = 20, ...svgProps }: IconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.75}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
      {...svgProps}
    >
      {ICONS[name]}
    </svg>
  )
}
