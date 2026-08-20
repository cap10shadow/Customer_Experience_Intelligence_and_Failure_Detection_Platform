import { CategoryBarChart, ChartFrame, TimeSeriesChart, type CategoryBarTone } from '@/shared/components/charts'
import { Panel, Stack } from '@/shared/components/layout'

import type { AnalyticsSeries } from '../../api'
import { AnalyticsLoadingState } from '../foundation'
import styles from './TrendVisualization.module.css'

export interface TrendVisualizationProps {
  /** The Gateway's real trend arrays. Undefined until the Analytics fetch resolves. */
  series?: AnalyticsSeries
  isLoading?: boolean
}

/**
 * The visual reading of the same real trend data the narrative cards
 * above state in words -- five charts, each backed 1:1 by one array of
 * `GET /api/v1/analytics/trends` (which the Gateway sources from
 * `anomaly_service`'s own `/api/v1/trends` summary, per
 * `analytics_aggregator.py`).
 *
 * | Chart | Exact source |
 * |---|---|
 * | Complaint volume per day | `volumeTrend[].date` / `.count` |
 * | Average sentiment score per day | `sentimentTrend[].date` / `.averageScore` |
 * | Complaints by category | `categoryTrend[].category` / `.count` |
 * | Complaints by region | `regionTrend[].region` / `.count` |
 * | Complaints by urgency | `urgencyTrend[].urgency` / `.count` |
 *
 * Nothing here is computed, smoothed, forecast, ranked, or annotated
 * with an interpretation -- the charts render exactly the values the
 * backend returned, in the order it returned them. A section with no
 * returned observations renders nothing at all rather than an empty
 * axis, so an absent capability can never look like a measured zero.
 *
 * Sits *below* the narratives, not above them: Analytics' frozen shape
 * is Trend → Narrative → Supporting Evidence, never Chart →
 * Interpretation (see `TrendAnalysis`), so the charts are the supporting
 * evidence for a statement already made in words.
 */
export function TrendVisualization({ series, isLoading = false }: TrendVisualizationProps) {
  if (isLoading) {
    return (
      <Panel>
        <AnalyticsLoadingState label="Loading trend charts" />
      </Panel>
    )
  }

  if (!series) {
    return null
  }

  const hasAnySeries =
    series.volume.length > 0 ||
    series.sentiment.length > 0 ||
    series.category.length > 0 ||
    series.region.length > 0 ||
    series.urgency.length > 0

  if (!hasAnySeries) {
    return null
  }

  return (
    <Panel>
      <Stack gap={4}>
        <p className={styles.heading}>Supporting charts</p>
        <div className={styles.grid}>
          {series.volume.length > 0 ? (
            <div className={styles.fullWidth}>
              <ChartFrame
                title="Complaint volume per day"
                description="Complaints recorded on each day the platform observed activity in this period. Days with no recorded complaints are not returned by the backend and are not drawn."
                rowHeaderLabel="Date"
                rowHeaders={series.volume.map((point) => point.date)}
                columns={[{ header: 'Complaints', values: series.volume.map((point) => String(point.count)) }]}
              >
                <TimeSeriesChart
                  points={series.volume.map((point) => ({ label: point.date, value: point.count }))}
                  ariaLabel="Complaint volume per day"
                  includeZero
                />
              </ChartFrame>
            </div>
          ) : null}

          {series.sentiment.length > 0 ? (
            <div className={styles.fullWidth}>
              <ChartFrame
                title="Average sentiment score per day"
                description="The mean sentiment score nlp_service assigned to the complaints recorded on each day. Negative values sit below the dashed zero line."
                rowHeaderLabel="Date"
                rowHeaders={series.sentiment.map((point) => point.date)}
                columns={[
                  {
                    header: 'Average score',
                    values: series.sentiment.map((point) => point.averageScore.toFixed(2)),
                  },
                  {
                    // `labelCounts` is real, per-day enrichment output
                    // that nothing in the UI surfaced before. It is
                    // reported verbatim rather than charted, because a
                    // label breakdown is a different measure from the
                    // score the chart plots -- two measures never share
                    // one axis.
                    header: 'Sentiment labels',
                    values: series.sentiment.map((point) => formatLabelCounts(point.labelCounts)),
                  },
                ]}
              >
                <TimeSeriesChart
                  points={series.sentiment.map((point) => ({ label: point.date, value: point.averageScore }))}
                  ariaLabel="Average sentiment score per day"
                  formatValue={(value) => value.toFixed(1)}
                  showZeroBaseline
                />
              </ChartFrame>
            </div>
          ) : null}

          {series.category.length > 0 ? (
            <ChartFrame
              title="Complaints by category"
              description="Total complaints per category across this period, as classified by nlp_service."
              rowHeaderLabel="Category"
              rowHeaders={series.category.map((point) => humanizeToken(point.category))}
              columns={[{ header: 'Complaints', values: series.category.map((point) => String(point.count)) }]}
            >
              <CategoryBarChart
                ariaLabel="Complaint count by category"
                items={series.category.map((point) => ({ label: humanizeToken(point.category), value: point.count }))}
              />
            </ChartFrame>
          ) : null}

          {series.region.length > 0 ? (
            <ChartFrame
              title="Complaints by region"
              description="Total complaints per customer region across this period. Regions are recorded as supplied at ingestion and are not normalized by the platform."
              rowHeaderLabel="Region"
              rowHeaders={series.region.map((point) => point.region)}
              columns={[{ header: 'Complaints', values: series.region.map((point) => String(point.count)) }]}
            >
              <CategoryBarChart
                ariaLabel="Complaint count by region"
                items={series.region.map((point) => ({ label: point.region, value: point.count }))}
              />
            </ChartFrame>
          ) : null}

          {series.urgency.length > 0 ? (
            <ChartFrame
              title="Complaints by urgency"
              description="Total complaints per urgency level across this period, as classified by nlp_service."
              rowHeaderLabel="Urgency"
              rowHeaders={series.urgency.map((point) => humanizeToken(point.urgency))}
              columns={[{ header: 'Complaints', values: series.urgency.map((point) => String(point.count)) }]}
            >
              <CategoryBarChart
                ariaLabel="Complaint count by urgency"
                items={series.urgency.map((point) => ({
                  label: humanizeToken(point.urgency),
                  value: point.count,
                  tone: urgencyTone(point.urgency),
                }))}
              />
            </ChartFrame>
          ) : null}
        </div>
      </Stack>
    </Panel>
  )
}

/** Presentation only: `delivery_issue` -> `Delivery issue`. Never re-maps, merges, or renames a backend value. */
function humanizeToken(token: string): string {
  const spaced = token.replace(/_/g, ' ').trim()
  return spaced.charAt(0).toUpperCase() + spaced.slice(1)
}

/**
 * Urgency is the one charted dimension that is a genuine operational
 * *state*, so it is the one that uses the reserved `--color-status-*`
 * tones. The mapping is a direct read of the backend's urgency enum, and
 * every bar still carries its own text label -- colour is never the sole
 * signal (the same rule `StatusIndicator` already documents).
 */
function urgencyTone(urgency: string): CategoryBarTone {
  switch (urgency.toLowerCase()) {
    case 'critical':
      return 'critical'
    case 'high':
      return 'warning'
    case 'medium':
      return 'info'
    default:
      return 'neutral'
  }
}

function formatLabelCounts(labelCounts: Record<string, number>): string {
  const entries = Object.entries(labelCounts)
  if (entries.length === 0) {
    return '—'
  }
  return entries.map(([label, count]) => `${humanizeToken(label)}: ${count}`).join(', ')
}
