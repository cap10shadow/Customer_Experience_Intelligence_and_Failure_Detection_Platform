import { useEffect, useRef, type KeyboardEvent, type ReactNode } from 'react'

import { Panel } from '@/shared/components/layout'
import { Icon } from '@/shared/icons'

import styles from './Modal.module.css'

export interface ModalProps {
  title: string
  children: ReactNode
  footer?: ReactNode
  onClose: () => void
}

/**
 * The platform's first true modal dialog -- `--color-scrim` (tokens.css)
 * was defined and marked "future use" with no consumer until now. Unlike
 * `CopilotPanel` (`aria-modal="false"`, deliberately non-blocking so the
 * workspace stays usable behind it), this is a real blocking dialog:
 * `aria-modal="true"`, closes on Escape and on scrim click, and traps Tab
 * focus while open -- for genuine confirm/cancel decisions (e.g. the
 * Ingestion workspace's pre-submit confirmation) where the rest of the
 * page must not remain interactive.
 */
export function Modal({ title, children, footer, onClose }: ModalProps) {
  const dialogRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const previouslyFocused = document.activeElement as HTMLElement | null
    dialogRef.current?.querySelector<HTMLElement>('button:not(:disabled), [href], input, textarea')?.focus()
    return () => previouslyFocused?.focus()
  }, [])

  const handleKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key === 'Escape') {
      onClose()
      return
    }
    if (event.key !== 'Tab') return

    const focusable = dialogRef.current?.querySelectorAll<HTMLElement>(
      'button:not(:disabled), [href], input:not(:disabled), textarea:not(:disabled)',
    )
    if (!focusable || focusable.length === 0) return
    const first = focusable[0]
    const last = focusable[focusable.length - 1]

    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault()
      last.focus()
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault()
      first.focus()
    }
  }

  return (
    <div className={styles.scrim} onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-heading"
        className={styles.wrapper}
        onKeyDown={handleKeyDown}
      >
        <Panel elevated className={styles.panel}>
          <header className={styles.header}>
            <h2 id="modal-heading" className={styles.title}>
              {title}
            </h2>
            <button type="button" className={styles.closeButton} onClick={onClose} aria-label="Close dialog">
              <Icon name="close" size={18} />
            </button>
          </header>
          <div className={styles.body}>{children}</div>
          {footer ? <footer className={styles.footer}>{footer}</footer> : null}
        </Panel>
      </div>
    </div>
  )
}
