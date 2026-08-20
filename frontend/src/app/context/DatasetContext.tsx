// This file exports both `DatasetProvider` (a component) and the
// `useDatasetContext`/`useOptionalDatasetContext` hooks, mirroring
// AuthContext.tsx's own justified single-file exception to
// react-refresh/only-export-components (same reasoning: this is a real,
// app-wide context, not a workspace-local one that could live in three
// files under one workspace).
/* eslint-disable react-refresh/only-export-components */
import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react'

/** Exported for tests that need to seed a selected dataset before rendering (e.g. `localStorage.setItem(DATASET_STORAGE_KEY, 'dataset-1')`) without depending on the provider's own setter being reachable from outside a component tree. */
export const DATASET_STORAGE_KEY = 'oi-platform:selected-dataset-id'
const DATASET_NAME_STORAGE_KEY = 'oi-platform:selected-dataset-name'

export interface SelectedDataset {
  id: string
  name: string
}

export interface DatasetContextValue {
  /** The Dataset every dataset-aware workspace (Dashboard, Analytics, and going forward Investigations/Recommendations) scopes itself to. `null` means genuinely "nothing selected yet" -- never defaulted to a fabricated/first dataset silently. */
  selectedDatasetId: string | null
  /**
   * The selected dataset's name, captured at selection time by whoever
   * calls `setSelectedDataset` (the Data workspace, which already has the
   * real name from its own list/detail fetch). Read by other workspaces'
   * context banners (Dashboard, Analytics) so they can show which dataset
   * they are scoped to without issuing their own extra
   * `GET /v1/datasets/{id}` request -- each workspace's own Gateway call
   * remains the only fetch it makes. Can lag a rename made elsewhere
   * until the dataset is reselected; that staleness is an accepted
   * trade-off for not duplicating a network call in every workspace.
   */
  selectedDatasetName: string | null
  setSelectedDataset: (dataset: SelectedDataset | null) => void
}

const DatasetContext = createContext<DatasetContextValue | null>(null)

function readStoredValue(key: string): string | null {
  if (typeof window === 'undefined') return null
  try {
    return window.localStorage.getItem(key)
  } catch {
    // Private-browsing/storage-disabled: fail open to "nothing selected" rather than crash.
    return null
  }
}

export interface DatasetProviderProps {
  children: ReactNode
}

/**
 * Global dataset selection (docs/DECISIONS.md AD-12) -- mounted in
 * `AppProviders.tsx` alongside `AuthProvider`, outside the router, so it
 * survives navigation between every workspace exactly like the session
 * does. Persisted to `localStorage` (matching the existing theme/
 * sidebar-collapsed precedent in `app/theme/ThemeProvider.tsx` and
 * `app/layouts/AppShell.tsx`) with a lazy `useState` initializer, rather
 * than a route param or query string: Dataset is cross-cutting app
 * state that scopes every workspace at once, not a single entity a URL
 * points to (see `routePaths.ts`'s own explicit precedent against
 * `?id=` query strings for entity identity). A hard refresh therefore
 * keeps the same dataset selected; switching datasets is a client-side
 * state change that every mounted workspace's data hook reacts to via
 * its own effect dependency array -- never a place where Dataset A's
 * data can silently remain on screen after switching to Dataset B.
 */
export function DatasetProvider({ children }: DatasetProviderProps) {
  const [selectedDatasetId, setSelectedDatasetIdState] = useState<string | null>(() => readStoredValue(DATASET_STORAGE_KEY))
  const [selectedDatasetName, setSelectedDatasetNameState] = useState<string | null>(() => readStoredValue(DATASET_NAME_STORAGE_KEY))

  const setSelectedDataset = useCallback((dataset: SelectedDataset | null) => {
    setSelectedDatasetIdState(dataset?.id ?? null)
    setSelectedDatasetNameState(dataset?.name ?? null)
    if (typeof window === 'undefined') return
    try {
      if (dataset) {
        window.localStorage.setItem(DATASET_STORAGE_KEY, dataset.id)
        window.localStorage.setItem(DATASET_NAME_STORAGE_KEY, dataset.name)
      } else {
        window.localStorage.removeItem(DATASET_STORAGE_KEY)
        window.localStorage.removeItem(DATASET_NAME_STORAGE_KEY)
      }
    } catch {
      // Storage unavailable -- the in-memory state above still works for this session.
    }
  }, [])

  const value = useMemo<DatasetContextValue>(
    () => ({ selectedDatasetId, selectedDatasetName, setSelectedDataset }),
    [selectedDatasetId, selectedDatasetName, setSelectedDataset],
  )

  return <DatasetContext.Provider value={value}>{children}</DatasetContext.Provider>
}

export function useDatasetContext(): DatasetContextValue {
  const context = useContext(DatasetContext)
  if (context === null) {
    throw new Error('useDatasetContext must be used within a DatasetProvider.')
  }
  return context
}

/** Provider-tolerant variant for components that render standalone in tests -- mirrors `useOptionalAuth`'s identical rationale. */
export function useOptionalDatasetContext(): DatasetContextValue | null {
  return useContext(DatasetContext)
}
