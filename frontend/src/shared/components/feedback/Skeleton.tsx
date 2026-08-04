import { classNames } from '@/shared/utilities/classNames'

import styles from './Skeleton.module.css'

export interface SkeletonProps {
  width?: number | string
  height?: number | string
  /** 'full' for a pill/circle-capable shape (avatars), 'sm' for text-like corners. */
  radius?: 'sm' | 'full'
  className?: string
}

/** A loading placeholder shape. Purely decorative -- always `aria-hidden`; the containing `LoadingContainer` owns the announced loading state. */
export function Skeleton({ width = '100%', height = 16, radius = 'sm', className }: SkeletonProps) {
  return (
    <span
      aria-hidden="true"
      className={classNames(styles.skeleton, className)}
      style={{
        width,
        height,
        borderRadius: radius === 'full' ? 'var(--radius-full)' : undefined,
      }}
    />
  )
}
