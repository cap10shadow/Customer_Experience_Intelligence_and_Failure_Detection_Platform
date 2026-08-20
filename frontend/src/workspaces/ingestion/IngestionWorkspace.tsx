import { useId, useState, type FormEvent } from 'react'

import { ApiError, describeApiError } from '@/app/api/errors'
import { useDatasetContext } from '@/app/context/DatasetContext'
import { useOptionalAuth } from '@/auth/context/AuthContext'
import { AdvisoryNotice, EmptyState, ErrorBoundary, LoadingContainer } from '@/shared/components/feedback'
import { Grid, SectionContainer, Stack } from '@/shared/components/layout'
import { WorkspaceContainer } from '@/shared/components/page'
import { Button, Card, DataTable, Modal, type DataTableColumn } from '@/shared/components/primitives'
import { Badge, type BadgeTone } from '@/shared/components/utility'

import { createDataset } from './api'
import { AnalysisSummary } from './components/AnalysisSummary'
import { MappingClusterList } from './components/MappingReview'
import { RecentComplaints } from './components/RecentComplaints'
import { RowPreviewTable } from './components/RowPreview'
import { SubmissionResults } from './components/SubmissionResults'
import { UploadManifest } from './components/UploadManifest'
import { UploadPanel } from './components/UploadPanel'
import { ANALYSIS_PAGE_SIZE, useComplaintAnalysis } from './hooks/useComplaintAnalysis'
import { useComplaintSubmission } from './hooks/useComplaintSubmission'
import { useDataset } from './hooks/useDataset'
import { useDatasetArchive } from './hooks/useDatasetArchive'
import { useDatasetVersionFinalize } from './hooks/useDatasetVersionFinalize'
import { useDatasets } from './hooks/useDatasets'
import { useRecentComplaints } from './hooks/useRecentComplaints'
import { createAnalysisSessionId } from './utilities/sessionId'
import styles from './IngestionWorkspace.module.css'
import {
  DATASET_VERSION_IN_PROGRESS_STATUSES,
  DATASET_VERSION_STATUS_LABEL,
  type DatasetSummary,
  type DatasetVersion,
  type DatasetVersionStatus,
  type ParsedComplaintRow,
} from './types'

type IngestionStage = 'review' | 'submitting' | 'complete'

const STATUS_TONE: Record<DatasetVersionStatus, BadgeTone> = {
  draft: 'neutral',
  ingesting: 'info',
  processing: 'info',
  analyzing: 'info',
  ready: 'success',
  failed: 'critical',
  partially_completed: 'warning',
}

function VersionBadge({ version }: { version?: DatasetVersion }) {
  if (!version) return <Badge tone="neutral">No version yet</Badge>
  return (
    <Badge tone={STATUS_TONE[version.status]}>
      v{version.versionNumber} · {DATASET_VERSION_STATUS_LABEL[version.status]}
    </Badge>
  )
}

/**
 * Data / Ingestion Workspace -- the platform's entry point into the
 * operational intelligence lifecycle (docs/DECISIONS.md AD-12). A
 * Dataset is a persistent analytical workspace, not a pile of raw
 * records: nothing here can ingest, browse, or finalize data without a
 * real, selected Dataset (`useDatasetContext`) driving every call, and
 * no workspace-local fallback to a global/dataset-less view exists.
 *
 * Two real flows, both backed only by what the backend actually
 * supports:
 *  - No dataset selected -> dataset LIST (`useDatasets`) + "New dataset".
 *  - Dataset selected -> DETAIL: version banner, Upload -> Preview ->
 *    Confirm -> Ingest (existing components, unchanged), an explicit
 *    "Finalize & Analyze" action that drives the real synchronous
 *    pipeline (`useDatasetVersionFinalize`), and real version History
 *    (`useDataset`'s `data.versions`) so a prior version's state stays
 *    accessible after a dataset is extended.
 */
export function IngestionWorkspace() {
  const auth = useOptionalAuth()
  const canIngest = auth ? auth.hasRole('operator') : true
  const { selectedDatasetId, setSelectedDataset } = useDatasetContext()

  return (
    <WorkspaceContainer
      title="Data"
      description="Upload, extend, and analyze the datasets that drive every other workspace -- the real entry point into detection, investigation, and recommendation."
    >
      {selectedDatasetId ? (
        <DatasetDetailView
          datasetId={selectedDatasetId}
          canIngest={canIngest}
          onChangeDataset={() => setSelectedDataset(null)}
        />
      ) : (
        <DatasetListView
          canCreate={canIngest}
          onSelectDataset={(datasetId, name) => setSelectedDataset({ id: datasetId, name })}
        />
      )}
    </WorkspaceContainer>
  )
}

interface DatasetListViewProps {
  canCreate: boolean
  onSelectDataset: (datasetId: string, name: string) => void
}

function DatasetListView({ canCreate, onSelectDataset }: DatasetListViewProps) {
  const { data, isLoading, error, refetch } = useDatasets()
  const [isCreateOpen, setIsCreateOpen] = useState(false)

  return (
    <SectionContainer
      title="Datasets"
      description="Each dataset is its own persistent analytical workspace -- select one to ingest data and see its intelligence, or create a new, unrelated one."
      actions={
        canCreate ? (
          <Button variant="primary" onClick={() => setIsCreateOpen(true)}>
            + New dataset
          </Button>
        ) : null
      }
    >
      {error ? (
        <AdvisoryNotice title="Datasets could not be loaded" description={describeApiError(error, { subject: 'load datasets' })} />
      ) : (
        <ErrorBoundary boundaryLabel="Dataset list" onRetry={refetch} resetKeys={[isLoading]}>
          <LoadingContainer isLoading={isLoading} label="Loading datasets">
            {data && data.length > 0 ? (
              <Grid minColumnWidth={280} gap={4}>
                {data.map((dataset) => (
                  <DatasetCard key={dataset.id} dataset={dataset} onSelect={() => onSelectDataset(dataset.id, dataset.name)} />
                ))}
              </Grid>
            ) : (
              <EmptyState
                title="No datasets yet"
                description={
                  canCreate
                    ? 'Create your first dataset to start ingesting complaint records and generating real intelligence.'
                    : 'An operator has not created a dataset yet. Ingesting and creating datasets requires the operator role.'
                }
                action={
                  canCreate ? (
                    <Button variant="primary" onClick={() => setIsCreateOpen(true)}>
                      + New dataset
                    </Button>
                  ) : undefined
                }
              />
            )}
          </LoadingContainer>
        </ErrorBoundary>
      )}

      {isCreateOpen ? (
        <CreateDatasetModal
          onClose={() => setIsCreateOpen(false)}
          onCreated={(datasetId, name) => {
            setIsCreateOpen(false)
            refetch()
            onSelectDataset(datasetId, name)
          }}
        />
      ) : null}
    </SectionContainer>
  )
}

function DatasetCard({ dataset, onSelect }: { dataset: DatasetSummary; onSelect: () => void }) {
  return (
    <Card
      title={dataset.name}
      titleAccessory={
        <Stack gap={1} direction="row">
          {dataset.isLegacy ? <Badge tone="warning">DEMO / LEGACY</Badge> : null}
          <VersionBadge version={dataset.latestVersion} />
        </Stack>
      }
      description={dataset.description}
      footer={
        <Button variant="secondary" onClick={onSelect}>
          Open dataset
        </Button>
      }
    >
      <Stack gap={1}>
        <p className={styles.datasetMeta}>
          {dataset.currentVersion ? `${dataset.currentVersion.cumulativeRecordCount} records` : 'No finalized version yet'}
        </p>
        <p className={styles.datasetMeta}>
          {dataset.openIncidentCount !== undefined ? `${dataset.openIncidentCount} open incident${dataset.openIncidentCount === 1 ? '' : 's'}` : ''}
        </p>
        {dataset.currentVersion?.analysisCompletedAt ? (
          <p className={styles.datasetMeta}>Last analyzed: {new Date(dataset.currentVersion.analysisCompletedAt).toLocaleString()}</p>
        ) : null}
        <p className={styles.datasetMeta}>Created {new Date(dataset.insertedAt).toLocaleString()}</p>
      </Stack>
    </Card>
  )
}

function CreateDatasetModal({ onClose, onCreated }: { onClose: () => void; onCreated: (datasetId: string, name: string) => void }) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | undefined>(undefined)
  const nameId = useId()
  const descriptionId = useId()

  const handleCreate = async () => {
    const trimmedName = name.trim()
    if (!trimmedName) return

    setIsSubmitting(true)
    setError(undefined)
    try {
      const created = await createDataset({ name: trimmedName, description: description.trim() || undefined })
      onCreated(created.id, created.name)
    } catch (caught: unknown) {
      const apiError =
        caught instanceof ApiError ? caught : new ApiError({ code: 'UNKNOWN_ERROR', message: 'Failed to create this dataset.', status: 0 })
      setError(describeApiError(apiError, { subject: 'create this dataset' }))
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    void handleCreate()
  }

  return (
    <Modal
      title="New dataset"
      onClose={onClose}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button variant="primary" onClick={() => void handleCreate()} disabled={isSubmitting || name.trim().length === 0}>
            {isSubmitting ? 'Creating…' : 'Create dataset'}
          </Button>
        </>
      }
    >
      <form onSubmit={handleSubmit}>
        <Stack gap={3}>
          <p>A new, unrelated analytical workspace -- its own version history, isolated from every other dataset.</p>
          <div className={styles.field}>
            <label htmlFor={nameId} className={styles.label}>
              Name (required)
            </label>
            <input id={nameId} type="text" className={styles.input} value={name} onChange={(event) => setName(event.target.value)} />
          </div>
          <div className={styles.field}>
            <label htmlFor={descriptionId} className={styles.label}>
              Description (optional)
            </label>
            <textarea
              id={descriptionId}
              className={styles.textarea}
              rows={3}
              value={description}
              onChange={(event) => setDescription(event.target.value)}
            />
          </div>
          {error ? (
            <p role="alert" className={styles.error}>
              {error}
            </p>
          ) : null}
        </Stack>
      </form>
    </Modal>
  )
}

interface DatasetDetailViewProps {
  datasetId: string
  canIngest: boolean
  onChangeDataset: () => void
}

function DatasetDetailView({ datasetId, canIngest, onChangeDataset }: DatasetDetailViewProps) {
  const { data, isLoading, error, refetch } = useDataset(datasetId)

  const [rows, setRows] = useState<ParsedComplaintRow[]>([])
  const [analysisSessionId, setAnalysisSessionId] = useState(createAnalysisSessionId)
  const [stage, setStage] = useState<IngestionStage>('review')
  const [isConfirmOpen, setIsConfirmOpen] = useState(false)
  const { isSubmitting, results, error: submitError, submit, reset } = useComplaintSubmission(datasetId)
  const { data: recentData, isLoading: recentLoading, error: recentError, refetch: refetchRecent } = useRecentComplaints(datasetId)
  const { isSubmitting: isFinalizing, result: finalizeResult, error: finalizeError, finalize, reset: resetFinalize } = useDatasetVersionFinalize()
  const { isArchiving, error: archiveError, archive } = useDatasetArchive()
  const [isArchiveConfirmOpen, setIsArchiveConfirmOpen] = useState(false)
  const analysis = useComplaintAnalysis(datasetId, analysisSessionId, rows)

  const readyCount = analysis.analysis ? analysis.analysis.summary.accepted + analysis.analysis.summary.auto_normalized : 0
  const unresolvedCount = analysis.analysis
    ? analysis.analysis.summary.suggested_mapping + analysis.analysis.summary.needs_review
    : 0
  const rejectedCount = analysis.analysis?.summary.rejected ?? 0
  const isProcessing = data?.currentVersion ? DATASET_VERSION_IN_PROGRESS_STATUSES.includes(data.currentVersion.status) : false

  const handleRowsParsed = (parsedRows: ParsedComplaintRow[]) => {
    setRows((previous) => [...previous, ...parsedRows])
  }

  const handleManualRowAdded = (row: ParsedComplaintRow) => {
    setRows((previous) => [...previous, row])
  }

  const handleRemoveRow = (rowId: string) => {
    setRows((previous) => previous.filter((row) => row.rowId !== rowId))
  }

  const handleConfirmIngest = () => {
    setIsConfirmOpen(false)
    setStage('submitting')
    submit(rows, analysisSessionId)
      .then(() => setStage('complete'))
      .then(refetchRecent)
  }

  const handleStartOver = () => {
    setRows([])
    setAnalysisSessionId(createAnalysisSessionId())
    reset()
    resetFinalize()
    setStage('review')
  }

  const [isFinalizeConfirmOpen, setIsFinalizeConfirmOpen] = useState(false)
  const nextVersionNumber = data?.latestVersion?.versionNumber ?? 1
  const priorCumulativeCount = data?.currentVersion?.cumulativeRecordCount ?? 0

  const handleFinalize = () => {
    setIsFinalizeConfirmOpen(false)
    finalize(datasetId).then(() => refetch())
  }

  const handleArchive = () => {
    setIsArchiveConfirmOpen(false)
    // Archiving removes this dataset from listings/lookups (its versions,
    // complaints, and every downstream intelligence entity stay intact --
    // never a hard delete). Clear the now-invalid selection immediately
    // rather than waiting for the next fetch to 404, so DatasetContext
    // can never point at an archived dataset as if it were still active.
    void archive(datasetId).then((succeeded) => {
      if (succeeded) onChangeDataset()
    })
  }

  if (error) {
    return (
      <Stack gap={6}>
        <SectionContainer
          title={data?.name ?? 'Dataset'}
          actions={<Button variant="secondary" onClick={onChangeDataset}>Change dataset</Button>}
        >
          <AdvisoryNotice title="This dataset could not be loaded" description={describeApiError(error, { subject: 'load this dataset' })} />
        </SectionContainer>
        <SectionContainer title="Upload, recent records, and version history">
          <AdvisoryNotice
            title="Not shown while this dataset fails to load"
            description="Uploading, recent records, and version history all depend on this dataset's details, which could not be loaded above. Retry loading the dataset before continuing."
          />
          <div className={styles.bannerRow}>
            <Button variant="secondary" onClick={refetch}>
              Retry
            </Button>
          </div>
        </SectionContainer>
      </Stack>
    )
  }

  return (
    <Stack gap={6}>
      <SectionContainer
        title={data?.name ?? 'Dataset'}
        description={data?.description}
        actions={
          <Stack direction="row" gap={2}>
            <Button variant="secondary" onClick={onChangeDataset}>
              Change dataset
            </Button>
            <Button
              variant="secondary"
              onClick={() => setIsArchiveConfirmOpen(true)}
              disabled={data?.isLegacy}
              title={data?.isLegacy ? 'The demo/legacy dataset cannot be archived.' : undefined}
            >
              Archive dataset
            </Button>
          </Stack>
        }
      >
        <LoadingContainer isLoading={isLoading} label="Loading dataset">
          <div className={styles.bannerRow}>
            {data?.isLegacy ? <Badge tone="warning">DEMO / LEGACY</Badge> : null}
            <VersionBadge version={data?.latestVersion} />
            {data?.currentVersion ? (
              <p className={styles.datasetMeta}>{data.currentVersion.cumulativeRecordCount} records analyzed</p>
            ) : (
              <p className={styles.datasetMeta}>No version has been finalized and analyzed yet.</p>
            )}
            {isProcessing ? <Badge tone="info">Analysis in progress -- refresh to check status</Badge> : null}
            {data?.currentVersion?.status === 'failed' && data.currentVersion.failureReason ? (
              <p className={styles.error}>{data.currentVersion.failureReason}</p>
            ) : null}
          </div>
        </LoadingContainer>
      </SectionContainer>

      {isArchiveConfirmOpen ? (
        <Modal
          title="Archive this dataset?"
          onClose={() => setIsArchiveConfirmOpen(false)}
          footer={
            <>
              <Button variant="secondary" onClick={() => setIsArchiveConfirmOpen(false)}>
                Cancel
              </Button>
              <Button variant="primary" onClick={handleArchive} disabled={isArchiving}>
                {isArchiving ? 'Archiving…' : 'Archive dataset'}
              </Button>
            </>
          }
        >
          <p>
            &quot;{data?.name}&quot; will no longer appear in the dataset list and cannot be selected for new work.
            Nothing is deleted -- its versions, ingested complaints, and every downstream intelligence (anomalies,
            incidents, root causes, business impact, recommendations) remain intact and unaffected. This action
            cannot be undone from this screen.
          </p>
          {archiveError ? (
            <AdvisoryNotice title="Archiving failed" description={describeApiError(archiveError, { subject: 'archive this dataset' })} />
          ) : null}
        </Modal>
      ) : null}

      <SectionContainer title="Upload &amp; ingest" description="Upload a file or add a complaint manually, then review before submitting.">
        {!canIngest ? (
          <AdvisoryNotice
            title="Ingesting complaints requires the operator role"
            description="Your account holds read access to the platform. Submitting records below will be refused by the platform; an operator or administrator can ingest data."
          />
        ) : null}

        {stage === 'review' ? (
          <Stack gap={6}>
            <UploadPanel onRowsParsed={handleRowsParsed} onManualRowAdded={handleManualRowAdded} />

            {rows.length > 0 ? (
              <Stack gap={3}>
                <UploadManifest rows={rows} />
                {analysis.error ? (
                  <AdvisoryNotice
                    title="Analysis failed"
                    description={describeApiError(analysis.error, { subject: 'analyze these rows' })}
                    action={
                      <Button variant="secondary" onClick={analysis.refresh}>
                        Retry
                      </Button>
                    }
                  />
                ) : null}
                {analysis.analysis ? (
                  <Stack gap={2} direction="row" align="center">
                    <AnalysisSummary totalRows={analysis.analysis.total_rows} summary={analysis.analysis.summary} />
                    <Button variant="secondary" onClick={analysis.refresh} disabled={analysis.isAnalyzing}>
                      {analysis.isAnalyzing ? 'Analyzing…' : 'Re-analyze'}
                    </Button>
                  </Stack>
                ) : null}
                <RowPreviewTable
                  rows={rows}
                  results={analysis.analysis?.results ?? []}
                  page={analysis.analysis?.page ?? analysis.page}
                  pageSize={ANALYSIS_PAGE_SIZE}
                  totalRows={analysis.analysis?.total_rows ?? rows.length}
                  onPageChange={analysis.setPage}
                  onRemoveRow={handleRemoveRow}
                  isLoading={analysis.isAnalyzing && !analysis.analysis}
                  isUpdating={analysis.isAnalyzing && !!analysis.analysis}
                />
                {analysis.analysis && analysis.analysis.pending_clusters.length > 0 ? (
                  <MappingClusterList clusters={analysis.analysis.pending_clusters} onResolved={analysis.refresh} />
                ) : null}
                <Stack gap={2}>
                  <p>
                    {readyCount} record{readyCount === 1 ? '' : 's'} ready to ingest
                    {unresolvedCount > 0 ? `, ${unresolvedCount} still need a mapping decision above` : ''}
                    {rejectedCount > 0 ? `, ${rejectedCount} invalid (excluded)` : ''}.
                  </p>
                  <div>
                    <Button
                      variant="primary"
                      disabled={!canIngest || readyCount === 0 || analysis.isAnalyzing}
                      onClick={() => setIsConfirmOpen(true)}
                    >
                      Ingest {readyCount} record{readyCount === 1 ? '' : 's'}
                    </Button>
                  </div>
                </Stack>
              </Stack>
            ) : null}
          </Stack>
        ) : null}

        {stage === 'submitting' ? (
          <p role="status" aria-live="polite">
            {isSubmitting ? 'Submitting this batch…' : 'Submitted.'}
          </p>
        ) : null}

        {submitError ? (
          <AdvisoryNotice title="Submission failed" description={describeApiError(submitError, { subject: 'submit this batch' })} />
        ) : null}

        {stage === 'complete' ? (
          <Stack gap={4}>
            <SubmissionResults results={results} onStartOver={handleStartOver} />
            <Stack gap={2}>
              <p>
                Records above are now part of this dataset&apos;s open draft (version {nextVersionNumber}) -- they
                have been ingested, but no analysis has run over them yet, and the Dashboard/Analytics intelligence
                for this dataset has not changed. Finalize this version to run the real analysis pipeline
                (enrichment, anomaly detection, incidents, root cause, business impact, and recommendations) over
                the dataset&apos;s full, cumulative record set.
              </p>
              <div>
                <Button
                  variant="primary"
                  onClick={() => setIsFinalizeConfirmOpen(true)}
                  disabled={isFinalizing || !canIngest}
                >
                  {isFinalizing ? 'Analyzing… this can take a while' : 'Finalize & Analyze'}
                </Button>
              </div>
              {finalizeError ? (
                <AdvisoryNotice
                  title="Finalize & Analyze failed"
                  description={describeApiError(finalizeError, { subject: 'finalize and analyze this version' })}
                />
              ) : null}
              {finalizeResult ? (
                <p>
                  Version {finalizeResult.versionNumber} finished with status{' '}
                  <strong>{DATASET_VERSION_STATUS_LABEL[finalizeResult.status]}</strong>
                  {finalizeResult.failureReason ? `: ${finalizeResult.failureReason}` : '.'}
                </p>
              ) : null}
            </Stack>
          </Stack>
        ) : null}

        {isConfirmOpen ? (
          <Modal
            title="Confirm ingestion"
            onClose={() => setIsConfirmOpen(false)}
            footer={
              <>
                <Button variant="secondary" onClick={() => setIsConfirmOpen(false)}>
                  Cancel
                </Button>
                <Button variant="primary" onClick={handleConfirmIngest}>
                  Ingest {readyCount} record{readyCount === 1 ? '' : 's'}
                </Button>
              </>
            }
          >
            <p>
              This submits every row to this dataset in one transaction. {readyCount} record{readyCount === 1 ? '' : 's'}{' '}
              {readyCount === 1 ? 'is' : 'are'} ready and will be created (or reported as a duplicate).
              {unresolvedCount > 0
                ? ` ${unresolvedCount} row${unresolvedCount === 1 ? '' : 's'} still needing a mapping decision will be rejected -- resolve them above first if you want them included.`
                : ''}
              {rejectedCount > 0 ? ` ${rejectedCount} structurally invalid row${rejectedCount === 1 ? '' : 's'} will be rejected.` : ''}
            </p>
          </Modal>
        ) : null}

        {isFinalizeConfirmOpen ? (
          <Modal
            title={`Finalize version ${nextVersionNumber}?`}
            onClose={() => setIsFinalizeConfirmOpen(false)}
            footer={
              <>
                <Button variant="secondary" onClick={() => setIsFinalizeConfirmOpen(false)}>
                  Cancel
                </Button>
                <Button variant="primary" onClick={handleFinalize}>
                  Finalize & Analyze
                </Button>
              </>
            }
          >
            <p>
              This closes the current draft into finalized version {nextVersionNumber} and re-runs the full analysis
              pipeline over all {priorCumulativeCount + results.filter((r) => r.outcome === 'created').length} records
              in this dataset (not just what was just ingested). This can take a while and cannot be undone once
              started. Previous finalized versions remain available in Version History.
            </p>
          </Modal>
        ) : null}
      </SectionContainer>

      <Grid minColumnWidth={460} gap={6}>
        <ErrorBoundary boundaryLabel="Recent Complaints" onRetry={refetchRecent} resetKeys={[recentLoading]}>
          <SectionContainer title="Recently ingested" description="What has actually entered this dataset, most recent first.">
            {recentError ? (
              <AdvisoryNotice
                title="Recent complaints could not be loaded"
                description={describeApiError(recentError, { subject: 'load recent complaints' })}
              />
            ) : (
              <RecentComplaints items={recentData?.items ?? []} isLoading={recentLoading} />
            )}
          </SectionContainer>
        </ErrorBoundary>

        <SectionContainer title="Version history" description="Every prior finalized version of this dataset remains accessible -- extending it never destroys what came before.">
          <VersionHistoryTable versions={data?.versions ?? []} isLoading={isLoading} />
        </SectionContainer>
      </Grid>
    </Stack>
  )
}

function VersionHistoryTable({ versions, isLoading }: { versions: DatasetVersion[]; isLoading: boolean }) {
  const sorted = [...versions].sort((a, b) => b.versionNumber - a.versionNumber)
  const columns: DataTableColumn<DatasetVersion>[] = [
    { key: 'version', header: 'Version', render: (row) => `v${row.versionNumber}` },
    { key: 'status', header: 'Status', render: (row) => <Badge tone={STATUS_TONE[row.status]}>{DATASET_VERSION_STATUS_LABEL[row.status]}</Badge> },
    { key: 'cumulative', header: 'Cumulative records', render: (row) => row.cumulativeRecordCount },
    { key: 'new', header: 'New records', render: (row) => row.newRecordCount },
    { key: 'completed', header: 'Analysis completed', render: (row) => (row.analysisCompletedAt ? new Date(row.analysisCompletedAt).toLocaleString() : '—') },
    { key: 'inserted', header: 'Created', render: (row) => new Date(row.insertedAt).toLocaleString() },
  ]

  return (
    <DataTable
      columns={columns}
      rows={sorted}
      rowKey={(row) => row.id}
      isLoading={isLoading}
      loadingLabel="Loading version history"
      emptyTitle="No versions yet"
      emptyDescription="Finalize this dataset's draft to create its first version."
    />
  )
}
