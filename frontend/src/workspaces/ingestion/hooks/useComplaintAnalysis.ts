import { useCallback, useEffect, useState } from 'react'

import { ApiError } from '@/app/api/errors'

import { analyzeComplaints, type ComplaintAnalyzeApiResponse } from '../api'
import { toAnalyzeRowInputs } from '../utilities/rowMapping'
import type { ParsedComplaintRow } from '../types'

export const ANALYSIS_PAGE_SIZE = 25

export interface UseComplaintAnalysisResult {
  analysis: ComplaintAnalyzeApiResponse | null
  isAnalyzing: boolean
  error: ApiError | null
  page: number
  setPage: (page: number) => void
  /** Re-runs `:analyze` with the SAME `analysisSessionId` -- safe to call after approving a mapping; occurrence counts are not inflated by re-analyzing the same session (see the mapping-persistence occurrence-session design). */
  refresh: () => void
}

/**
 * The backend, not the frontend, owns normalization/mapping/validation
 * (Ingestion Normalization & Mapping Layer plan). This hook's only job
 * is to call `POST :analyze` whenever the row set, page, or
 * `analysisSessionId` changes, and expose the resulting classification.
 * `analysisSessionId` is stable across re-analyzes within one
 * upload/review round (owned by the caller -- see DatasetDetailView) so
 * mapping occurrence counts stay correct even though this hook may
 * re-fire many times against the same rows (e.g. once per page change,
 * once after every mapping approval).
 */
export function useComplaintAnalysis(
  datasetId: string | null,
  analysisSessionId: string,
  rows: ParsedComplaintRow[],
): UseComplaintAnalysisResult {
  const [analysis, setAnalysis] = useState<ComplaintAnalyzeApiResponse | null>(null)
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [error, setError] = useState<ApiError | null>(null)
  const [page, setPage] = useState(1)
  const [refreshToken, setRefreshToken] = useState(0)

  const refresh = useCallback(() => setRefreshToken((token) => token + 1), [])

  // A row set change invalidates the current page's results -- start back at page 1
  // rather than showing a stale page number for a now-different row count.
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- mirrors useDataset's identical "reset on input change" branch.
    setPage(1)
  }, [rows])

  useEffect(() => {
    if (!datasetId || rows.length === 0) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- mirrors useDataset's identical "nothing to fetch" branch.
      setAnalysis(null)
      setError(null)
      return
    }

    const controller = new AbortController()
    setIsAnalyzing(true)
    setError(null)

    analyzeComplaints(
      datasetId,
      { analysis_session_id: analysisSessionId, rows: toAnalyzeRowInputs(rows) },
      { page, pageSize: ANALYSIS_PAGE_SIZE },
      { signal: controller.signal },
    )
      .then((response) => {
        if (controller.signal.aborted) return
        setAnalysis(response)
        setIsAnalyzing(false)
      })
      .catch((caught: unknown) => {
        if (controller.signal.aborted) return
        setError(
          caught instanceof ApiError ? caught : new ApiError({ code: 'UNKNOWN_ERROR', message: 'Failed to analyze these rows.', status: 0 }),
        )
        setIsAnalyzing(false)
      })

    return () => controller.abort()
    // eslint-disable-next-line react-hooks/exhaustive-deps -- refreshToken is a deliberate re-fetch trigger, not a value read in the effect body.
  }, [datasetId, analysisSessionId, rows, page, refreshToken])

  return { analysis, isAnalyzing, error, page, setPage, refresh }
}
