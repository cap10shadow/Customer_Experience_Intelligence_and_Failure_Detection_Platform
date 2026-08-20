import { Stack } from '@/shared/components/layout'

import { AdministrationEmptyState, AdministrationSection, AdministrationStatusBadge } from '../foundation'
import type { ConfigurationItem } from '../../types'
import { ReadOnlyConfigurationItemCard } from './ReadOnlyConfigurationItemCard'
import styles from './IntelligenceConfiguration.module.css'

/** Shape-only placeholder while loading -- never rendered as visible text; see PlatformOverview's identical LOADING_SERVICE_SHAPE precedent. */
const LOADING_ITEM_SHAPE: ConfigurationItem[] = Array.from({ length: 3 }, (_, index) => ({
  id: `loading-${index}`,
  name: '',
  whatItIs: '',
  governs: '',
  currentValue: '',
}))

export interface IntelligenceConfigurationProps {
  /** Real, currently-active Business Impact configuration values (Step 7.X G-05) -- undefined only before the first fetch resolves. */
  items?: ConfigurationItem[]
  isLoading?: boolean
}

/**
 * "How is platform intelligence configured?" -- ADM-004: greater
 * presentation weight than the three State-register sections, achieved
 * through pacing and spacing (the `.container` background and generous
 * internal spacing below), never through alarm colors, warning styling,
 * or interaction friction. Administration configures intelligence; it
 * never interprets intelligence -- nothing in this section renders live
 * classification results, current alert volumes, or any data that looks
 * like it is reporting on intelligence output.
 *
 * Step 7.X G-05: every item is real, currently-active Business Impact
 * engine configuration, sourced from business_impact_service via the
 * Gateway -- never a hardcoded frontend copy. Read-only: no edit/save
 * button, no mutation control, anywhere in this section (see
 * `ReadOnlyConfigurationItemCard`).
 */
export function IntelligenceConfiguration({ items, isLoading = false }: IntelligenceConfigurationProps) {
  const resolvedItems = items ?? LOADING_ITEM_SHAPE

  return (
    <AdministrationSection
      id="intelligence-configuration"
      title="Intelligence Configuration"
      description="How is platform intelligence configured? Values shown are current and read-only."
      register="configuration"
      statusBadge={<AdministrationStatusBadge isLive />}
    >
      <div className={styles.container}>
        {!isLoading && items && items.length === 0 ? (
          <AdministrationEmptyState
            title="No configuration values available"
            description="Intelligence configuration could not be retrieved for this request."
          />
        ) : (
          <Stack gap={5}>
            {resolvedItems.map((item) => (
              <ReadOnlyConfigurationItemCard key={item.id} item={item} isLoading={isLoading || !items} />
            ))}
          </Stack>
        )}
      </div>
    </AdministrationSection>
  )
}
