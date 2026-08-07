import { useAnalyticsContext } from '../../context'
import { ANALYSIS_PERIOD_LABEL } from '../../types'
import styles from './ScopeIndicator.module.css'

/**
 * UX-005: the one shared workspace-level scope every Analytics section
 * reads -- analysis period plus illustrative active filters. Lives once,
 * persistently, in the navigator; individual sections must never
 * restate it (contrast with Dashboard's Step 2 sections, which each
 * appended their own "reflecting {timeRangeLabel}" caption -- Analytics
 * deliberately does not repeat that pattern, per UX-005's explicit
 * "must NOT repeatedly restate the same scope").
 */
export function ScopeIndicator() {
  const { selectedAnalysisPeriod } = useAnalyticsContext()

  return (
    <div className={styles.scope}>
      <div>
        <span className={styles.label}>Analysis period</span>
        <span className={styles.value}>{ANALYSIS_PERIOD_LABEL[selectedAnalysisPeriod]}</span>
      </div>
      <div>
        <span className={styles.label}>Filters</span>
        <span className={styles.value}>None active</span>
      </div>
    </div>
  )
}
