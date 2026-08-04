import { useId } from 'react'
import { NavLink } from 'react-router-dom'

import type { IconName } from '@/shared/icons'
import { Icon } from '@/shared/icons'
import { classNames } from '@/shared/utilities/classNames'

import styles from './NavigationItem.module.css'

export interface NavigationItemProps {
  label: string
  path: string
  icon: IconName
  /** Hides the visible label (collapsed sidebar) -- the accessible name is preserved via `title`/`aria-label`, never dropped. */
  iconOnly?: boolean
  /** Extra context announced to assistive tech alongside the label (from NavigationItemConfig.description). */
  description?: string
}

/**
 * One entry in a navigation list. Uses `NavLink` so the active workspace
 * is both visually distinct (see .active) and correctly exposed as
 * `aria-current="page"` -- keyboard and screen-reader users get the same
 * orientation sighted users get from the highlight.
 */
export function NavigationItem({ label, path, icon, iconOnly = false, description }: NavigationItemProps) {
  const descriptionId = useId()

  return (
    <li>
      <NavLink
        to={path}
        end={path === '/'}
        title={iconOnly ? label : undefined}
        aria-label={iconOnly ? label : undefined}
        aria-describedby={description ? descriptionId : undefined}
        className={({ isActive }) => classNames(styles.item, isActive && styles.active, iconOnly && styles.iconOnly)}
      >
        <Icon name={icon} size={20} />
        {iconOnly ? null : <span className={styles.label}>{label}</span>}
      </NavLink>
      {description ? (
        <span id={descriptionId} className="visually-hidden">
          {description}
        </span>
      ) : null}
    </li>
  )
}
