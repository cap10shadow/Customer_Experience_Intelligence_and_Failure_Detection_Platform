import { useCallback, useState } from 'react'

import { ApiError } from '@/app/api/errors'

import { batchSubmitComplaints, type BatchRowApiOutcome } from '../api'
import { toAnalyzeRowInputs } from '../utilities/rowMapping'
import type { ComplaintSubmissionResult, ParsedComplaintRow } from '../types'

const OUTCOME_MAP: Record<BatchRowApiOutcome, ComplaintSubmissionResult['outcome']> = {
  created: 'created',
  duplicate: 'duplicate',
  rejected: 'rejected',
}

export interface UseComplaintSubmissionResult {
  isSubmitting: boolean
  results: ComplaintSubmissionResult[]
  error: ApiError | null
  /**
   * Submits every row in `rows` in ONE `POST .../complaints:batch` call
   * -- a single transaction, not one request per row. The response
   * accounts for every row (`outcomes.length === rows.length` always,
   * enforced server-side): each becomes `created`/`duplicate`/`rejected`
   * here, never silently dropped.
   */
  submit: (rows: ParsedComplaintRow[], analysisSessionId: string) => Promise<ComplaintSubmissionResult[]>
  reset: () => void
}

/** The Data workspace's write hook, scoped to one dataset. */
export function useComplaintSubmission(datasetId: string | null): UseComplaintSubmissionResult {
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [results, setResults] = useState<ComplaintSubmissionResult[]>([])
  const [error, setError] = useState<ApiError | null>(null)

  const submit = useCallback(
    async (rows: ParsedComplaintRow[], analysisSessionId: string): Promise<ComplaintSubmissionResult[]> => {
      if (!datasetId || rows.length === 0) {
        return []
      }
      setIsSubmitting(true)
      setError(null)
      setResults([])

      try {
        const response = await batchSubmitComplaints(datasetId, {
          analysis_session_id: analysisSessionId,
          rows: toAnalyzeRowInputs(rows),
        })
        const mapped: ComplaintSubmissionResult[] = response.outcomes.map((outcome) => ({
          rowNumber: outcome.row_number,
          outcome: OUTCOME_MAP[outcome.outcome],
          message:
            outcome.outcome === 'created'
              ? 'Ingested successfully.'
              : outcome.reason ?? (outcome.outcome === 'duplicate' ? 'This record already exists.' : 'This row was rejected.'),
          complaintId: outcome.complaint_id,
        }))
        setResults(mapped)
        setIsSubmitting(false)
        return mapped
      } catch (caught: unknown) {
        const apiError =
          caught instanceof ApiError ? caught : new ApiError({ code: 'UNKNOWN_ERROR', message: 'Failed to submit this batch.', status: 0 })
        setError(apiError)
        setIsSubmitting(false)
        return []
      }
    },
    [datasetId],
  )

  const reset = useCallback(() => {
    setResults([])
    setError(null)
  }, [])

  return { isSubmitting, results, error, submit, reset }
}
