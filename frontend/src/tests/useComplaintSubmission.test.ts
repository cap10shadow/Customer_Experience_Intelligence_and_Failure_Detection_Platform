import { describe, expect, it, vi, afterEach } from 'vitest'
import { act, renderHook, waitFor } from '@testing-library/react'

import { useComplaintSubmission } from '@/workspaces/ingestion/hooks/useComplaintSubmission'
import type { ParsedComplaintRow } from '@/workspaces/ingestion/types'

function jsonResponse(body: unknown, status = 200) {
  return { status, ok: status >= 200 && status < 300, text: async () => JSON.stringify(body) } as Response
}

function row(rowId: string, complaintText: string): ParsedComplaintRow {
  return { rowId, complaintText }
}

describe('useComplaintSubmission', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('submits the whole row set in ONE request to :batch, not one request per row', async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(
      jsonResponse({
        dataset_id: 'dataset-1',
        dataset_version_id: 'version-1',
        total_rows: 2,
        created_count: 1,
        duplicate_count: 1,
        rejected_count: 0,
        outcomes: [
          { row_number: 1, outcome: 'created', complaint_id: 'complaint-1' },
          { row_number: 2, outcome: 'duplicate', reason: 'duplicate of existing complaint' },
        ],
      }),
    )
    vi.stubGlobal('fetch', fetchMock)

    const { result } = renderHook(() => useComplaintSubmission('dataset-1'))

    let outcome: Awaited<ReturnType<typeof result.current.submit>> = []
    await act(async () => {
      outcome = await result.current.submit(
        [row('row-1', 'A brand new complaint about packaging.'), row('row-2', 'An already-ingested complaint.')],
        'session-1',
      )
    })

    expect(fetchMock).toHaveBeenCalledTimes(1)
    const calledUrl = fetchMock.mock.calls[0][0] as string
    expect(calledUrl).toContain('/complaints:batch')

    expect(outcome).toEqual([
      { rowNumber: 1, outcome: 'created', message: 'Ingested successfully.', complaintId: 'complaint-1' },
      { rowNumber: 2, outcome: 'duplicate', message: 'duplicate of existing complaint', complaintId: undefined },
    ])
    await waitFor(() => expect(result.current.isSubmitting).toBe(false))
    expect(result.current.results).toEqual(outcome)
  })

  it('classifies a rejected row distinctly from duplicate/created, and every row is accounted for', async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(
      jsonResponse({
        dataset_id: 'dataset-1',
        dataset_version_id: 'version-1',
        total_rows: 1,
        created_count: 0,
        duplicate_count: 0,
        rejected_count: 1,
        outcomes: [{ row_number: 1, outcome: 'rejected', reason: 'complaint_text: invalid_format' }],
      }),
    )
    vi.stubGlobal('fetch', fetchMock)

    const { result } = renderHook(() => useComplaintSubmission('dataset-1'))

    let outcome: Awaited<ReturnType<typeof result.current.submit>> = []
    await act(async () => {
      outcome = await result.current.submit([row('row-1', 'short')], 'session-1')
    })

    expect(outcome).toEqual([{ rowNumber: 1, outcome: 'rejected', message: 'complaint_text: invalid_format', complaintId: undefined }])
  })
})
