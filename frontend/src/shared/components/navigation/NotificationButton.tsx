import { Icon } from '@/shared/icons'
import { classNames } from '@/shared/utilities/classNames'

import styles from './NotificationButton.module.css'

export interface NotificationButtonProps {
  /** Whether unread notifications exist. Not wired to any real data source in this phase -- callers pass it explicitly once a notification feed exists. */
  hasUnread?: boolean
  onClick?: () => void
  className?: string
}

/** The persistent top navigation's notification entry point. Indicates unread state with a dot *and* an accessible-name change, not color alone. */
export function NotificationButton({ hasUnread = false, onClick, className }: NotificationButtonProps) {
  return (
    <button
      type="button"
      className={classNames(styles.button, className)}
      onClick={onClick}
      aria-label={hasUnread ? 'Notifications (unread)' : 'Notifications'}
    >
      <Icon name="bell" size={20} />
      {hasUnread ? <span className={styles.dot} aria-hidden="true" /> : null}
    </button>
  )
}
