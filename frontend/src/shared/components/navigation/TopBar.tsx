import type { BreadcrumbSegment } from '@/shared/types/navigation'
import { Icon } from '@/shared/icons'

import { Breadcrumbs } from './Breadcrumbs'
import { NotificationButton } from './NotificationButton'
import { SearchBox } from './SearchBox'
import { UserMenu } from './UserMenu'
import styles from './TopBar.module.css'

export interface TopBarProps {
  breadcrumbSegments: BreadcrumbSegment[]
  onOpenMobileNav: () => void
}

/**
 * Persistent top navigation, per the frozen architecture. Owns
 * orientation (breadcrumbs) and account-level actions (search,
 * notifications, user menu) -- it never owns workspace-specific
 * controls; those belong to WorkspaceHeader.
 */
export function TopBar({ breadcrumbSegments, onOpenMobileNav }: TopBarProps) {
  return (
    <header className={styles.topbar}>
      <div className={styles.leading}>
        <button
          type="button"
          className={styles.mobileMenuButton}
          onClick={onOpenMobileNav}
          aria-label="Open navigation"
        >
          <Icon name="menu" size={20} />
        </button>
        <Breadcrumbs segments={breadcrumbSegments} />
      </div>
      <div className={styles.trailing}>
        <div className={styles.searchSlot}>
          <SearchBox />
        </div>
        <NotificationButton />
        <UserMenu
          userName="Operations User"
          items={[
            { label: 'Profile', onSelect: () => {} },
            { label: 'Preferences', onSelect: () => {} },
            { label: 'Sign out', onSelect: () => {} },
          ]}
        />
      </div>
    </header>
  )
}
