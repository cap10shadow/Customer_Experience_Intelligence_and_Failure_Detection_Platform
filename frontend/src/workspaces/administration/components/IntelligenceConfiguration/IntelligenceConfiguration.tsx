import { Stack } from '@/shared/components/layout'

import { AdministrationSection } from '../foundation'
import type { ConfigurationItem } from '../../types'
import { ConfigurationItemCard } from './ConfigurationItemCard'
import styles from './IntelligenceConfiguration.module.css'

const CONFIGURATION_ITEMS: ConfigurationItem[] = [
  {
    id: 'anomaly-severity-threshold-high',
    name: 'Anomaly Severity Threshold -- High',
    whatItIs: 'The complaint-spike magnitude above which an anomaly is classified as High severity.',
    governs: 'Determines when a complaint spike is classified as High-severity for Incident Correlation, which in turn shapes which anomalies are grouped into an Incident.',
    currentValue: '3.0x baseline',
  },
  {
    id: 'urgency-classification-keywords',
    name: 'Urgency Classification Keywords',
    whatItIs: 'The keyword set the NLP pipeline uses to flag a complaint as urgent.',
    governs: 'Determines which complaints are enriched with an "urgent" classification before trend and anomaly analysis runs.',
    currentValue: '18 keywords configured',
  },
  {
    id: 'alert-policy-critical-incidents',
    name: 'Alert Policy -- Critical Incidents',
    whatItIs: 'The notification policy applied when an Incident reaches Critical business impact.',
    governs: 'Determines who is notified, and how quickly, once Business Impact Analysis classifies an Incident as Critical.',
    currentValue: 'Notify Operations Managers immediately',
  },
]

export interface IntelligenceConfigurationProps {
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
 */
export function IntelligenceConfiguration({ isLoading = false }: IntelligenceConfigurationProps) {
  return (
    <AdministrationSection
      id="intelligence-configuration"
      title="Intelligence Configuration"
      description="How is platform intelligence configured?"
      register="configuration"
    >
      <div className={styles.container}>
        <Stack gap={5}>
          {CONFIGURATION_ITEMS.map((item) => (
            <ConfigurationItemCard key={item.id} item={item} isLoading={isLoading} />
          ))}
        </Stack>
      </div>
    </AdministrationSection>
  )
}
