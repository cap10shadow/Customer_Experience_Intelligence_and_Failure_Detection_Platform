import { forwardRef } from 'react'

import { Icon } from '@/shared/icons'
import { classNames } from '@/shared/utilities/classNames'

import styles from './CopilotLauncher.module.css'

export interface CopilotLauncherProps {
  isOpen: boolean
  onClick: () => void
}

/**
 * The persistent floating entry point (architecture §4/§32) -- a single
 * icon button, always visible, never covering the workspace. Toggles the
 * panel; its own accessible name changes with open state so a screen
 * reader announces the actual effect of activating it, the same
 * convention `NotificationButton`'s unread-state label change uses.
 */
export const CopilotLauncher = forwardRef<HTMLButtonElement, CopilotLauncherProps>(function CopilotLauncher(
  { isOpen, onClick },
  ref,
) {
  return (
    <button
      ref={ref}
      type="button"
      className={classNames(styles.launcher, isOpen && styles.launcherOpen)}
      onClick={onClick}
      aria-haspopup="dialog"
      aria-expanded={isOpen}
      aria-label={isOpen ? 'Close Copilot' : 'Open Copilot'}
    >
      <Icon name={isOpen ? 'close' : 'chat'} size={22} />
    </button>
  )
})
