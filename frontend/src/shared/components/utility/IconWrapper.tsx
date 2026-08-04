import { classNames } from '@/shared/utilities/classNames'
import { Icon, type IconName } from '@/shared/icons'

export type IconSize = 'sm' | 'md' | 'lg' | 'xl'

const SIZE_PX: Record<IconSize, number> = { sm: 16, md: 20, lg: 24, xl: 32 }

export interface IconWrapperProps {
  icon: IconName
  size?: IconSize
  /**
   * When provided, the icon becomes a meaningful, screen-reader-announced
   * element (`role="img"` + `aria-label`). Omit it when the icon is purely
   * decorative next to its own visible text label -- duplicating the
   * label onto the icon would make screen readers announce it twice.
   */
  label?: string
  className?: string
}

/**
 * The accessible, token-sized wrapper every other component uses instead
 * of the low-level `Icon` directly -- it is the single place an icon's
 * size is resolved from the `--icon-size-*` scale and the single place
 * the decorative-vs-meaningful accessibility decision is made.
 */
export function IconWrapper({ icon, size = 'md', label, className }: IconWrapperProps) {
  return (
    <span
      className={classNames(className)}
      style={{ display: 'inline-flex', flexShrink: 0 }}
      role={label ? 'img' : undefined}
      aria-label={label}
    >
      <Icon name={icon} size={SIZE_PX[size]} aria-hidden={label ? undefined : 'true'} />
    </span>
  )
}
