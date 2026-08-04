import { useId, useState, type FormEvent } from 'react'

import { Icon } from '@/shared/icons'
import { classNames } from '@/shared/utilities/classNames'

import styles from './SearchBox.module.css'

export interface SearchBoxProps {
  placeholder?: string
  /** No-op by default -- this phase establishes the input's architecture only; wiring it to real search is a future phase's business logic. */
  onSearch?: (query: string) => void
  className?: string
}

/** A real, accessible, keyboard-operable search input -- not wired to any backend yet, deliberately, per this phase's scope. */
export function SearchBox({ placeholder = 'Search', onSearch, className }: SearchBoxProps) {
  const [value, setValue] = useState('')
  const labelId = useId()

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault()
    onSearch?.(value)
  }

  return (
    <form role="search" onSubmit={handleSubmit} className={classNames(styles.form, className)}>
      <label htmlFor={labelId} className="visually-hidden">
        {placeholder}
      </label>
      <Icon name="search" size={16} />
      <input
        id={labelId}
        type="search"
        className={styles.input}
        placeholder={placeholder}
        value={value}
        onChange={(event) => setValue(event.target.value)}
      />
    </form>
  )
}
