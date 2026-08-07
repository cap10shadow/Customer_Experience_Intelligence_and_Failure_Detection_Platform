import { AdministrationEmptyState, AdministrationSection } from '../foundation'
import type { AuditEntry } from '../../types'
import { AuditEntryRow } from './AuditEntryRow'
import styles from './AuditChangeHistory.module.css'

const DEFAULT_ENTRIES: AuditEntry[] = [
  {
    id: 'entry-3',
    occurredAt: '2026-08-05 09:14 UTC',
    actor: 'A. Ferreira',
    action: 'updated the Anomaly Severity Threshold -- High configuration item.',
    from: '2.5x baseline',
    to: '3.0x baseline',
  },
  {
    id: 'entry-2',
    occurredAt: '2026-07-29 16:02 UTC',
    actor: 'System (SSO provisioning)',
    action: 'added a user to the Operations Manager role.',
    from: 'No role assigned',
    to: 'Operations Manager',
  },
  {
    id: 'entry-1',
    occurredAt: '2026-07-19 11:47 UTC',
    actor: 'R. Okafor',
    action: 'connected a new external system under Data Sources & Integrations.',
    from: 'Not connected',
    to: 'Connected (Support desk)',
  },
]

export interface AuditChangeHistoryProps {
  isLoading?: boolean
  /** Illustrative business data -- defaults to three entries; pass an empty array to exercise the honest "no actions recorded yet" empty state. */
  entries?: AuditEntry[]
}

/**
 * "What has changed, and who changed it?" -- ADM-001/ADM-003: complete
 * administrative traceability, presented as a permanent, read-only
 * ledger. Nothing here modifies configuration -- every entry is already
 * in the past. Rendered as a semantic `<ol>` of static rows (see
 * `AuditEntryRow`), never a notification list, never a feed with
 * unread/new state.
 */
export function AuditChangeHistory({ isLoading = false, entries = DEFAULT_ENTRIES }: AuditChangeHistoryProps) {
  const hasEntries = entries.length > 0

  return (
    <AdministrationSection
      id="audit-change-history"
      title="Audit & Change History"
      description="What has changed, and who changed it?"
      register="record"
    >
      {!hasEntries && !isLoading ? (
        <AdministrationEmptyState
          title="No administrative actions have been recorded yet"
          description="Every configuration change, user management action, integration change, and policy update will be permanently recorded here as it happens."
        />
      ) : (
        <ol className={styles.ledger} aria-label="Administrative change history, most recent first">
          {(isLoading ? DEFAULT_ENTRIES : entries).map((entry) => (
            <AuditEntryRow key={entry.id} entry={entry} isLoading={isLoading} />
          ))}
        </ol>
      )}
    </AdministrationSection>
  )
}
