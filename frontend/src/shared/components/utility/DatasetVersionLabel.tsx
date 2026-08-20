import { DATASET_VERSION_STATUS_LABEL, type DatasetDetail } from '@/workspaces/ingestion/types'

export interface DatasetVersionLabelProps {
  /** The selected dataset's name (or id, as a last-resort fallback) -- always shown, even before `detail` has loaded. */
  name: string
  /** This dataset's real detail fetch (`useDataset`). `undefined`/`null` while loading -- the version/status text is only shown once the backend has actually confirmed it, never guessed. */
  detail?: DatasetDetail | null
}

/**
 * "Dataset · vN · Status" for workspace headers (Dashboard, Analytics) that
 * scope their intelligence to one dataset and need to say, honestly, which
 * finalized version that intelligence reflects -- never claiming a version
 * is current before the backend confirms it (`detail` still loading or
 * `null` renders the name alone, not a fabricated placeholder version).
 */
export function DatasetVersionLabel({ name, detail }: DatasetVersionLabelProps) {
  const version = detail?.currentVersion
  if (!version) {
    return <span>Dataset: {name}</span>
  }

  const lastAnalyzed = version.analysisCompletedAt ? new Date(version.analysisCompletedAt).toLocaleString() : null

  return (
    <span>
      Dataset: {name} · v{version.versionNumber} · {DATASET_VERSION_STATUS_LABEL[version.status]}
      {lastAnalyzed ? ` · Last analyzed: ${lastAnalyzed}` : ''}
    </span>
  )
}
