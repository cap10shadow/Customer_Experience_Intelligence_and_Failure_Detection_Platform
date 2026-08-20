import type { TrendNarrative } from '../types'
import type {
  AnalyticsApiResponse,
  CategoryTrendPointApi,
  RegionTrendPointApi,
  SentimentTrendPointApi,
  UrgencyTrendPointApi,
  VolumeTrendPointApi,
} from './types'

export interface AnalyticsViewModel {
  trends: TrendNarrative[]
  /**
   * The Gateway's real trend arrays, carried through unchanged for the
   * chart layer (`TrendVisualization`).
   *
   * Before this existed, `toAnalyticsViewModel` reduced five populated
   * numeric series -- up to a full year of daily volume, every category,
   * every region, every sentiment observation -- to at most three
   * sentences each, and discarded the rest. The platform was fetching
   * real trend data on every Analytics load and then throwing almost all
   * of it away.
   *
   * Deliberately the raw API points, not a re-shaped copy: no sorting,
   * no bucketing, no aggregation, no derived percentage or delta. If a
   * number is drawn, `anomaly_service` computed it -- the same
   * "transform, never invent" boundary the narrative builders below
   * already observe.
   */
  series: AnalyticsSeries
  warnings: string[]
}

export interface AnalyticsSeries {
  volume: VolumeTrendPointApi[]
  category: CategoryTrendPointApi[]
  region: RegionTrendPointApi[]
  sentiment: SentimentTrendPointApi[]
  urgency: UrgencyTrendPointApi[]
}

/**
 * Turns each real trend array into a Trend -> Narrative -> Supporting
 * Evidence card (TrendAnalysis's frozen shape) using pure factual
 * presentation of the numbers the Gateway already returned -- naming a
 * specific returned entry and its count, or counting how many entries
 * were returned. Never a comparative/ranking/evaluative/causal word
 * ("most common," "highest," "improving," "driven by," etc.) and never a
 * new calculation (no sum/average/min/max/change). Even though
 * anomaly_service happens to return categories/regions/urgency sorted by
 * count, presenting that ordering as "most common" would itself be an
 * analytical interpretation this adapter has no capability to make (Part
 * 5 rectification) -- so entries are described individually, by name and
 * count only, never by rank. This keeps trend-calculation ownership
 * entirely in anomaly_service and narrative-formatting ownership entirely
 * in this adapter, matching Batch 2 SS10's "Gateway/frontend transform,
 * never invent" boundary.
 */
export function toAnalyticsViewModel(response: AnalyticsApiResponse): AnalyticsViewModel {
  const trends = [
    buildVolumeNarrative(response.volumeTrend, response.period),
    buildCategoryNarrative(response.categoryTrend, response.period),
    buildRegionNarrative(response.regionTrend, response.period),
    buildSentimentNarrative(response.sentimentTrend, response.period),
    buildUrgencyNarrative(response.urgencyTrend, response.period),
  ].filter((trend): trend is TrendNarrative => trend !== null)

  return {
    trends,
    series: {
      volume: response.volumeTrend,
      category: response.categoryTrend,
      region: response.regionTrend,
      sentiment: response.sentimentTrend,
      urgency: response.urgencyTrend,
    },
    warnings: response.warnings,
  }
}

function buildVolumeNarrative(points: VolumeTrendPointApi[], period: string): TrendNarrative | null {
  if (points.length === 0) {
    return null
  }
  const [first] = points
  const last = points[points.length - 1]
  return {
    id: 'complaint-volume-trend',
    trend: `${last.count} complaint(s) were recorded on ${last.date}.`,
    narrative: `Complaint volume data contains ${points.length} returned observation(s) for the ${period}.`,
    evidence: `${first.count} complaint(s) were recorded on ${first.date}.`,
  }
}

function buildCategoryNarrative(points: CategoryTrendPointApi[], period: string): TrendNarrative | null {
  if (points.length === 0) {
    return null
  }
  const [first, second] = points
  return {
    id: 'category-trend',
    trend: `${first.category} recorded ${first.count} complaint(s) in the returned trend data.`,
    narrative: `Category trend data contains ${points.length} returned observation(s) for the ${period}.`,
    evidence: second
      ? `${second.category} recorded ${second.count} complaint(s) in the returned trend data.`
      : 'No additional categories were returned in this window.',
  }
}

function buildRegionNarrative(points: RegionTrendPointApi[], period: string): TrendNarrative | null {
  if (points.length === 0) {
    return null
  }
  const [first, second] = points
  return {
    id: 'region-trend',
    trend: `${first.region} recorded ${first.count} complaint(s) in the returned trend data.`,
    narrative: `Region trend data contains ${points.length} returned observation(s) for the ${period}.`,
    evidence: second
      ? `${second.region} recorded ${second.count} complaint(s) in the returned trend data.`
      : 'No additional regions were returned in this window.',
  }
}

function buildUrgencyNarrative(points: UrgencyTrendPointApi[], period: string): TrendNarrative | null {
  if (points.length === 0) {
    return null
  }
  const [first, second] = points
  return {
    id: 'urgency-trend',
    trend: `${first.urgency} recorded ${first.count} complaint(s) in the returned trend data.`,
    narrative: `Urgency trend data contains ${points.length} returned observation(s) for the ${period}.`,
    evidence: second
      ? `${second.urgency} recorded ${second.count} complaint(s) in the returned trend data.`
      : 'No additional urgency levels were returned in this window.',
  }
}

function buildSentimentNarrative(points: SentimentTrendPointApi[], period: string): TrendNarrative | null {
  if (points.length === 0) {
    return null
  }
  const last = points[points.length - 1]
  const labelSummary = Object.entries(last.labelCounts)
    .map(([label, count]) => `${label}: ${count}`)
    .join(', ')
  return {
    id: 'sentiment-trend',
    trend: `An average sentiment score of ${last.averageScore} was recorded on ${last.date}.`,
    narrative: labelSummary
      ? `Sentiment labels recorded on ${last.date}: ${labelSummary}.`
      : `No sentiment labels were recorded on ${last.date}.`,
    evidence: `Sentiment trend data contains ${points.length} returned observation(s) for the ${period}.`,
  }
}
