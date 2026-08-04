import { classNames } from '@/shared/utilities/classNames'

export interface DividerProps {
  orientation?: 'horizontal' | 'vertical'
  className?: string
}

/** A semantic `<hr>` for horizontal rules (correctly announced by assistive tech); a decorative div for vertical rules, since HTML has no vertical-rule element. */
export function Divider({ orientation = 'horizontal', className }: DividerProps) {
  if (orientation === 'vertical') {
    return (
      <div
        role="separator"
        aria-orientation="vertical"
        className={classNames(className)}
        style={{ width: 1, alignSelf: 'stretch', backgroundColor: 'var(--color-border-subtle)' }}
      />
    )
  }

  return (
    <hr
      className={classNames(className)}
      style={{ border: 'none', borderTop: '1px solid var(--color-border-subtle)', margin: 0, width: '100%' }}
    />
  )
}
