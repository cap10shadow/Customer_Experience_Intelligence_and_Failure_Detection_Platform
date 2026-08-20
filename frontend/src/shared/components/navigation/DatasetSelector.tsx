import { useEffect, useRef } from 'react'

import { useOptionalDatasetContext } from '@/app/context/DatasetContext'
import { Icon } from '@/shared/icons'
import { useDisclosure } from '@/shared/hooks/useDisclosure'
import { DATASET_VERSION_STATUS_LABEL } from '@/workspaces/ingestion/types'
import { useDatasets } from '@/workspaces/ingestion/hooks/useDatasets'

import styles from './DatasetSelector.module.css'

/**
 * The global active-dataset control (top navigation) -- makes the existing,
 * app-wide `DatasetContext` visible and switchable from anywhere, not just
 * from the Data workspace's own local "Change dataset" button. Reuses the
 * Data workspace's own `useDatasets()` list fetch (the one place this
 * dataset list is fetched for chrome purposes) and writes through the same
 * `setSelectedDataset` every workspace already reacts to -- no new
 * per-workspace dataset state, no duplicate fetching logic.
 */
export function DatasetSelector() {
  const datasetContext = useOptionalDatasetContext()
  const { data, isLoading, refetch } = useDatasets()
  const { isOpen, close, toggle } = useDisclosure()
  const wrapperRef = useRef<HTMLDivElement>(null)
  const triggerRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    if (!isOpen) return

    const handlePointerDown = (event: MouseEvent) => {
      if (wrapperRef.current && !wrapperRef.current.contains(event.target as Node)) {
        close()
      }
    }
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        close()
        triggerRef.current?.focus()
      }
    }

    document.addEventListener('mousedown', handlePointerDown)
    document.addEventListener('keydown', handleKeyDown)
    return () => {
      document.removeEventListener('mousedown', handlePointerDown)
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [isOpen, close])

  // Standalone render (tests, storybook-style usage outside DatasetProvider) -- render nothing rather than throw.
  if (!datasetContext) return null

  const { selectedDatasetId, selectedDatasetName, setSelectedDataset } = datasetContext
  const selected = data?.find((dataset) => dataset.id === selectedDatasetId)
  // Prefer currentVersion (the highest READY version -- what Dashboard/
  // Analytics actually display) over latestVersion (the highest version
  // number regardless of status, e.g. the empty draft finalize() always
  // re-opens). Falls back to latestVersion only when nothing has ever
  // reached READY, so a brand-new dataset still shows its draft state.
  // Without this, finalizing a version immediately re-opens a new empty
  // draft, and this switcher -- visible on every page, including
  // Dashboard/Analytics -- would show "vN+1 * Draft" right next to
  // those workspaces' own header, which correctly shows "vN * Ready" for
  // the very same dataset: two parts of the same screen disagreeing
  // about which version the displayed intelligence belongs to.
  const displayVersion = selected ? (selected.currentVersion ?? selected.latestVersion) : undefined
  const triggerLabel = selected
    ? `${selected.name}${displayVersion ? ` · v${displayVersion.versionNumber} · ${DATASET_VERSION_STATUS_LABEL[displayVersion.status]}` : ''}`
    : (selectedDatasetName ?? 'No dataset selected')

  return (
    <div className={styles.wrapper} ref={wrapperRef}>
      <button
        type="button"
        ref={triggerRef}
        className={styles.trigger}
        onClick={() => {
          toggle()
          refetch()
        }}
        aria-haspopup="menu"
        aria-expanded={isOpen}
      >
        <span className={styles.label}>{triggerLabel}</span>
        <Icon name="chevronDown" size={14} />
      </button>
      {isOpen ? (
        <div role="menu" aria-label="Select active dataset" className={styles.menu}>
          {isLoading ? <p className={styles.hint}>Loading datasets…</p> : null}
          {!isLoading && (!data || data.length === 0) ? <p className={styles.hint}>No datasets exist yet.</p> : null}
          {data?.map((dataset) => {
            const menuItemVersion = dataset.currentVersion ?? dataset.latestVersion
            return (
              <button
                key={dataset.id}
                type="button"
                role="menuitem"
                className={styles.menuItem}
                aria-current={dataset.id === selectedDatasetId}
                onClick={() => {
                  close()
                  setSelectedDataset({ id: dataset.id, name: dataset.name })
                }}
              >
                <span className={styles.menuItemName}>{dataset.name}</span>
                <span className={styles.menuItemMeta}>
                  {menuItemVersion
                    ? `v${menuItemVersion.versionNumber} · ${DATASET_VERSION_STATUS_LABEL[menuItemVersion.status]}`
                    : 'No version yet'}
                </span>
              </button>
            )
          })}
        </div>
      ) : null}
    </div>
  )
}
