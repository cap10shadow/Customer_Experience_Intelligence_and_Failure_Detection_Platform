import { useId, useState } from 'react'

import { Panel, Stack } from '@/shared/components/layout'

import type { RecommendationDecisionApiValue } from '../../api'
import styles from './DecisionForm.module.css'

export interface DecisionFormProps {
  /** Undefined for a Recommendation with no decision recorded yet -- pre-selects nothing rather than defaulting to a fabricated choice. */
  currentDecision?: RecommendationDecisionApiValue
  isSubmitting: boolean
  errorMessage?: string
  onSubmit: (decision: RecommendationDecisionApiValue, note: string | undefined) => void
}

const DECISION_OPTIONS: { value: RecommendationDecisionApiValue; label: string }[] = [
  { value: 'pending', label: 'Pending' },
  { value: 'approved', label: 'Approved' },
  { value: 'rejected', label: 'Rejected' },
  { value: 'deferred', label: 'Deferred' },
]

/**
 * Real decision controls (Step 7.X G-01) -- the platform's one write
 * capability for Recommendations. No actor/owner field: the person
 * recording the decision is not modeled anywhere in this form, per
 * G-01's explicitly minimal scope. Submitting again overwrites the
 * prior decision (the backend's own documented, honest behavior given
 * no attribution exists yet) -- this form makes that visible by always
 * remaining available, never locking once a decision exists.
 */
export function DecisionForm({ currentDecision, isSubmitting, errorMessage, onSubmit }: DecisionFormProps) {
  const [decision, setDecision] = useState<RecommendationDecisionApiValue>(currentDecision ?? 'pending')
  const [note, setNote] = useState('')
  const decisionFieldId = useId()
  const noteFieldId = useId()

  return (
    <Panel>
      <form
        className={styles.form}
        onSubmit={(event) => {
          event.preventDefault()
          onSubmit(decision, note.trim() ? note.trim() : undefined)
        }}
      >
        <Stack gap={3}>
          <div className={styles.field}>
            <label htmlFor={decisionFieldId} className={styles.label}>
              {currentDecision ? 'Change decision' : 'Record a decision'}
            </label>
            <select
              id={decisionFieldId}
              className={styles.select}
              value={decision}
              disabled={isSubmitting}
              onChange={(event) => setDecision(event.target.value as RecommendationDecisionApiValue)}
            >
              {DECISION_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>

          <div className={styles.field}>
            <label htmlFor={noteFieldId} className={styles.label}>
              Note (optional)
            </label>
            <textarea
              id={noteFieldId}
              className={styles.textarea}
              value={note}
              disabled={isSubmitting}
              onChange={(event) => setNote(event.target.value)}
              rows={3}
            />
          </div>

          {errorMessage ? (
            <p role="alert" className={styles.error}>
              {errorMessage}
            </p>
          ) : null}

          <button type="submit" className={styles.submitButton} disabled={isSubmitting}>
            {isSubmitting ? 'Saving decision…' : 'Save decision'}
          </button>
        </Stack>
      </form>
    </Panel>
  )
}
