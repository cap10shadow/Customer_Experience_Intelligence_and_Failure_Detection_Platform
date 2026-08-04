import type { ReactNode } from 'react'

import { classNames } from '@/shared/utilities/classNames'

import styles from './ContentContainer.module.css'

export interface ContentContainerProps {
  children: ReactNode
  className?: string
}

/** Caps content width and applies consistent horizontal padding -- the one place "max content width" is decided, so every workspace's content reads at a comfortable line length on ultra-wide desktop monitors. */
export function ContentContainer({ children, className }: ContentContainerProps) {
  return <div className={classNames(styles.container, className)}>{children}</div>
}
