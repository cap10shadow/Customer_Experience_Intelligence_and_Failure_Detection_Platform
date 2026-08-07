import { AdministrationLoadingState } from '../foundation'
import type { AuditEntry } from '../../types'
import styles from './AuditEntryRow.module.css'

export interface AuditEntryRowProps {
  entry: AuditEntry
  isLoading?: boolean
}

/**
 * `AuditEntry.occurredAt` is authored in the human-readable
 * "YYYY-MM-DD HH:MM UTC" form used for both display and chronology --
 * that display text is frozen UX and must never change. The `<time>`
 * element's `datetime` attribute, however, is a separate, machine-read
 * value that HTML requires to be a "valid global date and time string"
 * (WHATWG): the literal `UTC` suffix is not a valid timezone designator
 * there, only `Z` or a numeric `±hh:mm` offset are. This converts the
 * authored display string into that ISO-8601 form for the attribute
 * only -- the visible text passed to `<time>` is untouched.
 */
function toIsoDateTimeAttribute(occurredAt: string): string {
  const match = /^(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}) UTC$/.exec(occurredAt)
  if (!match) {
    return occurredAt
  }
  const [, date, time] = match
  return `${date}T${time}:00Z`
}

/**
 * ADM-003: one permanent ledger row. Deliberately a plain, static `<li>`
 * -- never a `<button>`, never `aria-pressed`, never a "new"/unread
 * indicator, never a relative timestamp ("2m ago") as the primary time
 * reference. Every row shows full context (who, what, when, from what
 * value to what value) at equal visual weight to every other row --
 * nothing here is styled to draw more attention for being recent, which
 * is exactly what would make this read as an activity feed instead of an
 * immutable record.
 */
export function AuditEntryRow({ entry, isLoading = false }: AuditEntryRowProps) {
  if (isLoading) {
    return (
      <li className={styles.row}>
        <AdministrationLoadingState label="Loading audit entry" />
      </li>
    )
  }

  return (
    <li className={styles.row}>
      <time dateTime={toIsoDateTimeAttribute(entry.occurredAt)} className={styles.timestamp}>
        {entry.occurredAt}
      </time>
      <div className={styles.body}>
        <p className={styles.action}>
          <span className={styles.actor}>{entry.actor}</span> {entry.action}
        </p>
        <p className={styles.change}>
          Changed from <span className={styles.value}>{entry.from}</span> to <span className={styles.value}>{entry.to}</span>
        </p>
      </div>
    </li>
  )
}
