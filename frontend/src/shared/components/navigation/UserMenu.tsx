import { useEffect, useRef } from 'react'

import { Avatar } from '@/shared/components/utility'
import { Icon } from '@/shared/icons'
import { useDisclosure } from '@/shared/hooks/useDisclosure'

import styles from './UserMenu.module.css'

export interface UserMenuItem {
  label: string
  onSelect: () => void
}

export interface UserMenuProps {
  userName: string
  items: UserMenuItem[]
}

/**
 * The account entry point in the top navigation. A deliberately scoped
 * accessible-menu implementation: proper `menu`/`menuitem` roles,
 * `aria-expanded`, close-on-Escape, close-on-outside-click, and focus
 * returned to the trigger on close. Roving-tabindex arrow-key navigation
 * within the menu is not implemented -- out of scope for an
 * architectural foundation step with no real menu items yet; add it
 * alongside the first real UserMenu action.
 */
export function UserMenu({ userName, items }: UserMenuProps) {
  const { isOpen, close, toggle } = useDisclosure()
  const wrapperRef = useRef<HTMLDivElement>(null)
  const triggerRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    if (!isOpen) return

    const handlePointerDown = (event: MouseEvent) => {
      if (wrapperRef.current && !wrapperRef.current.contains(event.target as Node)) {
        close()
      }
    }
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        close()
        triggerRef.current?.focus()
      }
    }

    document.addEventListener('mousedown', handlePointerDown)
    document.addEventListener('keydown', handleKeyDown)
    return () => {
      document.removeEventListener('mousedown', handlePointerDown)
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [isOpen, close])

  return (
    <div className={styles.wrapper} ref={wrapperRef}>
      <button
        type="button"
        ref={triggerRef}
        className={styles.trigger}
        onClick={toggle}
        aria-haspopup="menu"
        aria-expanded={isOpen}
      >
        <Avatar name={userName} size="sm" />
        <span className={styles.name}>{userName}</span>
        <Icon name="chevronDown" size={14} />
      </button>
      {isOpen ? (
        <div role="menu" aria-label={`${userName} account menu`} className={styles.menu}>
          {items.map((item) => (
            <button
              key={item.label}
              type="button"
              role="menuitem"
              className={styles.menuItem}
              onClick={() => {
                close()
                item.onSelect()
              }}
            >
              {item.label}
            </button>
          ))}
        </div>
      ) : null}
    </div>
  )
}
