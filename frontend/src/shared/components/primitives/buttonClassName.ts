import { classNames } from '@/shared/utilities/classNames'

import styles from './Button.module.css'
import type { ButtonVariant } from './Button'

/** For the rare case of a link that must look like a Button (e.g. "View the Dashboard" after Ingestion completes) -- `<button>` cannot host a real `<Link>` navigation, so callers apply this class to their own anchor/`Link` instead of rendering `<Button>` itself. Kept in its own module (not `Button.tsx`) so that file exports only the component, per this repository's `react-refresh/only-export-components` convention. */
export function buttonClassName(variant: ButtonVariant = 'secondary', className?: string): string {
  return classNames(styles.button, styles[variant], className)
}
