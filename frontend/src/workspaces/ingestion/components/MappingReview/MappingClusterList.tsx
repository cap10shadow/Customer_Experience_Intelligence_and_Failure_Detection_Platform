import { useMemo, useState } from 'react'

import { AdvisoryNotice } from '@/shared/components/feedback'
import { Panel, Stack } from '@/shared/components/layout'
import { Button } from '@/shared/components/primitives'
import { Badge } from '@/shared/components/utility'
import { describeApiError } from '@/app/api/errors'

import type { PendingClusterSummaryApi } from '../../api'
import { useFieldMappingActions } from '../../hooks/useFieldMappingActions'
import styles from './MappingClusterList.module.css'

export interface MappingClusterListProps {
  clusters: PendingClusterSummaryApi[]
  /** Re-runs `:analyze` (same session) so newly-approved values show up immediately, without a page reload and without inflating occurrence counts. */
  onResolved: () => void
}

/**
 * The mapping review UI: "N values need mapping", clustered by unique
 * value (never per-row), one decision resolves every occurrence.
 * MEDIUM confidence (a curated registry match) gets Accept/Change;
 * LOW confidence (no system suggestion) gets Map/Keep as Other. Both
 * sections support multi-select + one bulk-approve action, so a large
 * upload never requires resolving hundreds of individual values.
 */
export function MappingClusterList({ clusters, onResolved }: MappingClusterListProps) {
  const medium = useMemo(() => clusters.filter((c) => c.confidence === 'medium').sort((a, b) => b.occurrence_count - a.occurrence_count), [clusters])
  const low = useMemo(() => clusters.filter((c) => c.confidence === 'low').sort((a, b) => b.occurrence_count - a.occurrence_count), [clusters])
  const actions = useFieldMappingActions()

  if (clusters.length === 0) return null

  return (
    <Panel>
      <Stack gap={4}>
        <p className={styles.heading}>
          {clusters.length} value{clusters.length === 1 ? '' : 's'} need mapping
        </p>
        {actions.error ? (
          <AdvisoryNotice title="A mapping action failed" description={describeApiError(actions.error, { subject: 'resolve this mapping' })} />
        ) : null}
        {medium.length > 0 ? (
          <ClusterSection
            title="Suggested mappings"
            description="A curated alias registry suggests these targets -- never applied automatically. Accept the suggestion or change it."
            clusters={medium}
            allowKeepAsOwn={false}
            actions={actions}
            onResolved={onResolved}
          />
        ) : null}
        {low.length > 0 ? (
          <ClusterSection
            title="Needs review"
            description="No system suggestion exists for these values. Map each to a canonical value, or keep it as its own value."
            clusters={low}
            allowKeepAsOwn
            actions={actions}
            onResolved={onResolved}
          />
        ) : null}
      </Stack>
    </Panel>
  )
}

interface ClusterSectionProps {
  title: string
  description: string
  clusters: PendingClusterSummaryApi[]
  allowKeepAsOwn: boolean
  actions: ReturnType<typeof useFieldMappingActions>
  onResolved: () => void
}

function ClusterSection({ title, description, clusters, allowKeepAsOwn, actions, onResolved }: ClusterSectionProps) {
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [bulkTarget, setBulkTarget] = useState('')

  const toggle = (mappingId: string) => {
    setSelected((previous) => {
      const next = new Set(previous)
      if (next.has(mappingId)) next.delete(mappingId)
      else next.add(mappingId)
      return next
    })
  }

  const handleBulkApprove = () => {
    const target = bulkTarget.trim()
    if (!target || selected.size === 0) return
    void actions.bulkApprove([...selected], target, () => {
      setSelected(new Set())
      setBulkTarget('')
      onResolved()
    })
  }

  // Only offer a dropdown for the bulk target when every selected cluster shares
  // the same enum-backed field (mixed-field selections fall back to free text).
  const bulkChoices = useMemo(() => {
    const selectedClusters = clusters.filter((c) => selected.has(c.mapping_id))
    if (selectedClusters.length === 0) return undefined
    const first = selectedClusters[0].valid_choices
    if (!first) return undefined
    const sameForAll = selectedClusters.every((c) => c.valid_choices?.join('|') === first.join('|'))
    return sameForAll ? first : undefined
  }, [clusters, selected])

  if (clusters.length === 0) return null

  return (
    <Stack gap={3}>
      <div>
        <p className={styles.sectionTitle}>{title}</p>
        <p className={styles.sectionDescription}>{description}</p>
      </div>

      {selected.size > 0 ? (
        <div className={styles.bulkBar}>
          <span>{selected.size} selected</span>
          {bulkChoices ? (
            <select className={styles.input} value={bulkTarget} onChange={(event) => setBulkTarget(event.target.value)} aria-label="Target value for all selected">
              <option value="">Select a value...</option>
              {bulkChoices.map((choice) => (
                <option key={choice} value={choice}>
                  {choice}
                </option>
              ))}
            </select>
          ) : (
            <input
              type="text"
              className={styles.input}
              placeholder="Target value for all selected"
              value={bulkTarget}
              onChange={(event) => setBulkTarget(event.target.value)}
            />
          )}
          <Button variant="primary" onClick={handleBulkApprove} disabled={bulkTarget.trim().length === 0}>
            Approve {selected.size} selected
          </Button>
        </div>
      ) : null}

      <ul className={styles.list}>
        {clusters.map((cluster) => (
          <ClusterRow
            key={cluster.mapping_id}
            cluster={cluster}
            isSelected={selected.has(cluster.mapping_id)}
            onToggleSelect={() => toggle(cluster.mapping_id)}
            allowKeepAsOwn={allowKeepAsOwn}
            actions={actions}
            onResolved={onResolved}
          />
        ))}
      </ul>
    </Stack>
  )
}

interface ClusterRowProps {
  cluster: PendingClusterSummaryApi
  isSelected: boolean
  onToggleSelect: () => void
  allowKeepAsOwn: boolean
  actions: ReturnType<typeof useFieldMappingActions>
  onResolved: () => void
}

function ClusterRow({ cluster, isSelected, onToggleSelect, allowKeepAsOwn, actions, onResolved }: ClusterRowProps) {
  const [customTarget, setCustomTarget] = useState(cluster.suggested_target_value ?? '')
  const isPending = actions.pendingIds.has(cluster.mapping_id)

  const handleApprove = (target: string) => {
    if (!target.trim()) return
    void actions.approve(cluster.mapping_id, target.trim(), onResolved)
  }

  return (
    <li className={styles.row}>
      <input type="checkbox" checked={isSelected} onChange={onToggleSelect} disabled={isPending} aria-label="Select for bulk approval" />
      <div className={styles.rowBody}>
        <div className={styles.rowHeader}>
          <span className={styles.value}>{cluster.example_values.join(' / ')}</span>
          <Badge tone="neutral">{cluster.occurrence_count} row{cluster.occurrence_count === 1 ? '' : 's'}</Badge>
          <span className={styles.field}>{cluster.field_name}</span>
        </div>
        <div className={styles.rowActions}>
          {cluster.suggested_target_value ? (
            <>
              <span className={styles.suggestion}>Suggested: {cluster.suggested_target_value}</span>
              <Button variant="primary" onClick={() => handleApprove(cluster.suggested_target_value ?? '')} disabled={isPending}>
                Accept
              </Button>
            </>
          ) : null}
          {cluster.valid_choices ? (
            <select
              className={styles.input}
              value={customTarget}
              onChange={(event) => setCustomTarget(event.target.value)}
              disabled={isPending}
              aria-label={`Map ${cluster.field_name} to`}
            >
              <option value="">Select a value...</option>
              {cluster.valid_choices.map((choice) => (
                <option key={choice} value={choice}>
                  {choice}
                </option>
              ))}
            </select>
          ) : (
            <input
              type="text"
              className={styles.input}
              placeholder="Map to..."
              value={customTarget}
              onChange={(event) => setCustomTarget(event.target.value)}
              disabled={isPending}
            />
          )}
          <Button variant="secondary" onClick={() => handleApprove(customTarget)} disabled={isPending || customTarget.trim().length === 0}>
            {cluster.suggested_target_value ? 'Change' : 'Map'}
          </Button>
          {allowKeepAsOwn ? (
            <Button
              variant="secondary"
              onClick={() => handleApprove(cluster.example_values[0])}
              disabled={isPending}
            >
              Keep as Other
            </Button>
          ) : null}
        </div>
      </div>
    </li>
  )
}
