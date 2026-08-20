import type { ButtonHTMLAttributes, ReactNode } from 'react'

import { classNames } from '@/shared/utilities/classNames'

import styles from './Button.module.css'

export type ButtonVariant = 'primary' | 'secondary' | 'danger' | 'ghost'

export interface ButtonProps extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'children'> {
  children: ReactNode
  variant?: ButtonVariant
  /** Shows an inline spinner and disables the button -- distinct from `disabled` so callers don't have to compute `disabled={isSubmitting || ...}` themselves. */
  loading?: boolean
}

/**
 * The platform's one shared button primitive. Every workspace previously
 * hand-rolled its own `<button>` styled per-component (DecisionForm,
 * DataSourcesIntegrations, etc.) -- this is the first reusable version,
 * adopted by new work (Data/Ingestion, root-cause actions, Administration)
 * going forward. Existing hand-rolled buttons are left as-is for this
 * pass rather than migrated wholesale (see docs/PROJECT_STATUS.md's
 * design-system gap note).
 */
export function Button({
  children,
  variant = 'secondary',
  loading = false,
  disabled,
  className,
  type = 'button',
  ...rest
}: ButtonProps) {
  return (
    <button
      type={type}
      className={classNames(styles.button, styles[variant], loading && styles.loading, className)}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      {...rest}
    >
      {loading ? <span className={styles.spinner} aria-hidden="true" /> : null}
      <span className={styles.label}>{children}</span>
    </button>
  )
}
