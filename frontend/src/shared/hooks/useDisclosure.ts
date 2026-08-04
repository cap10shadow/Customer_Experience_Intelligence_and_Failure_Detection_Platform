import { useCallback, useState } from 'react'

export interface Disclosure {
  isOpen: boolean
  open: () => void
  close: () => void
  toggle: () => void
}

/** Minimal open/close state, shared by every dismissible foundation component (menus, the mobile sidebar drawer, future dialogs/popovers). */
export function useDisclosure(initialState = false): Disclosure {
  const [isOpen, setIsOpen] = useState(initialState)

  const open = useCallback(() => setIsOpen(true), [])
  const close = useCallback(() => setIsOpen(false), [])
  const toggle = useCallback(() => setIsOpen((current) => !current), [])

  return { isOpen, open, close, toggle }
}
