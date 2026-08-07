import { useId, useState } from 'react'

import { Panel, Stack } from '@/shared/components/layout'
import { classNames } from '@/shared/utilities/classNames'

import { useAdministrationContext } from '../../context'
import { AdministrationLoadingState } from '../foundation'
import type { ConfigurationItem } from '../../types'
import styles from './ConfigurationItemCard.module.css'

export interface ConfigurationItemCardProps {
  item: ConfigurationItem
  isLoading?: boolean
}

/**
 * ADM-002: every configurable item presents, in this fixed order --
 * what it is, what downstream behavior it governs, its current
 * configured value, and only then the editing affordance. Inspection is
 * always the default rendering; editing is a distinct, deliberate mode
 * an administrator must explicitly enter via the single "Edit" toggle
 * below, tracked as this item's `selectedConfigurationId` in
 * `AdministrationContext` -- never the default state, and never
 * auto-saved (there is no persistence layer in this step; the draft
 * value is local component state only, discarded when editing ends).
 */
export function ConfigurationItemCard({ item, isLoading = false }: ConfigurationItemCardProps) {
  const { selectedConfigurationId, selectConfigurationItem } = useAdministrationContext()
  const isEditing = selectedConfigurationId === item.id
  const [draftValue, setDraftValue] = useState(item.currentValue)
  const valueInputId = useId()

  if (isLoading) {
    return (
      <Panel>
        <AdministrationLoadingState label="Loading configuration item" />
      </Panel>
    )
  }

  return (
    <Panel className={styles.item}>
      <Stack gap={3}>
        {/* 1. What it is */}
        <div>
          <p className={styles.name}>{item.name}</p>
          <p className={styles.whatItIs}>{item.whatItIs}</p>
        </div>

        {/* 2. What downstream behavior it governs */}
        <p className={styles.governs}>
          <span className={styles.governsLabel}>Governs</span> {item.governs}
        </p>

        {/* 3. Current configured value -- always shown, read-only unless editing */}
        <div className={styles.valueRow}>
          <label htmlFor={valueInputId} className={styles.valueLabel}>
            Current value
          </label>
          <input
            id={valueInputId}
            type="text"
            className={classNames(styles.valueInput, isEditing && styles.valueInputEditing)}
            value={isEditing ? draftValue : item.currentValue}
            readOnly={!isEditing}
            aria-readonly={!isEditing}
            onChange={(event) => isEditing && setDraftValue(event.target.value)}
          />
        </div>

        {/* 4. The edit affordance -- reachable only after 1-3, never presented first */}
        <button
          type="button"
          className={styles.editButton}
          aria-pressed={isEditing}
          onClick={() => {
            if (isEditing) {
              setDraftValue(item.currentValue)
              selectConfigurationItem(null)
            } else {
              selectConfigurationItem(item.id)
            }
          }}
        >
          {isEditing ? 'Done inspecting draft -- no change is saved' : 'Edit'}
        </button>
      </Stack>
    </Panel>
  )
}
