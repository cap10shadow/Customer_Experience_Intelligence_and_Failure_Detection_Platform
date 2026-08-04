import { PRIMARY_NAVIGATION } from '@/app/configuration/navigation.config'
import { Icon } from '@/shared/icons'
import { Logo } from '@/shared/components/utility'
import { classNames } from '@/shared/utilities/classNames'

import { NavigationGroup } from './NavigationGroup'
import { NavigationItem } from './NavigationItem'
import { SidebarSection } from './SidebarSection'
import styles from './Sidebar.module.css'

export interface SidebarProps {
  isCollapsed: boolean
  onToggleCollapse: () => void
  isMobileOpen: boolean
  onCloseMobile: () => void
}

/**
 * The persistent sidebar -- orientation, per the frozen navigation
 * architecture. Its entire content is driven by `PRIMARY_NAVIGATION`
 * (app/configuration/navigation.config.ts), so it never needs to change
 * when a future workspace is added; only the config does.
 */
export function Sidebar({ isCollapsed, onToggleCollapse, isMobileOpen, onCloseMobile }: SidebarProps) {
  return (
    <>
      {isMobileOpen ? (
        <button
          type="button"
          aria-label="Close navigation"
          className={styles.scrim}
          onClick={onCloseMobile}
        />
      ) : null}
      <nav
        aria-label="Primary"
        className={classNames(styles.sidebar, isCollapsed && styles.collapsed, isMobileOpen && styles.mobileOpen)}
      >
        <div className={styles.header}>
          <Logo compact={isCollapsed} />
          <button
            type="button"
            className={styles.collapseToggle}
            onClick={onToggleCollapse}
            aria-label={isCollapsed ? 'Expand navigation' : 'Collapse navigation'}
            aria-pressed={isCollapsed}
          >
            <Icon name="chevronRight" size={16} style={{ transform: isCollapsed ? 'none' : 'rotate(180deg)' }} />
          </button>
        </div>
        <div className={styles.nav}>
          <SidebarSection>
            <NavigationGroup label="Operational workspaces">
              {PRIMARY_NAVIGATION.map((item) => (
                <NavigationItem
                  key={item.id}
                  label={item.label}
                  path={item.path}
                  icon={item.icon}
                  description={item.description}
                  iconOnly={isCollapsed}
                />
              ))}
            </NavigationGroup>
          </SidebarSection>
        </div>
      </nav>
    </>
  )
}
