import { classNames } from '@/shared/utilities/classNames'
import { Icon } from '@/shared/icons'

import styles from './Avatar.module.css'

export interface AvatarProps {
  /** Full display name -- used to derive initials and as the accessible name when no image is available. */
  name?: string
  imageSrc?: string
  size?: 'sm' | 'md' | 'lg'
  className?: string
}

function getInitials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean)
  if (parts.length === 0) return ''
  if (parts.length === 1) return parts[0]!.slice(0, 2).toUpperCase()
  return `${parts[0]![0]}${parts[parts.length - 1]![0]}`.toUpperCase()
}

/** A user's visual identity -- image when available, initials next, a generic person icon as the final fallback (never a broken image). */
export function Avatar({ name, imageSrc, size = 'md', className }: AvatarProps) {
  const initials = name ? getInitials(name) : ''

  return (
    <span
      className={classNames(styles.avatar, styles[size], className)}
      role="img"
      aria-label={name ?? 'User avatar'}
    >
      {imageSrc ? (
        <img src={imageSrc} alt="" className={styles.image} />
      ) : initials ? (
        <span aria-hidden="true">{initials}</span>
      ) : (
        <Icon name="user" size={size === 'sm' ? 14 : size === 'lg' ? 22 : 18} />
      )}
    </span>
  )
}
