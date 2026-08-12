/**
 * Shape of GET /api/v1/analytics/trends's response body
 * (backend/services/gateway_service/app/schemas/analytics.py's
 * AnalyticsResponse). Every field here is a real anomaly_service trend
 * field passed through the Gateway -- there is deliberately no `patterns`,
 * `organizationalInsights`, `strategicOpportunities`, or
 * `recommendationEffectiveness` field here, because no backend capability
 * produces any of those today (Part 5's capability audit).
 */
export interface VolumeTrendPointApi {
  date: string
  count: number
}

export interface CategoryTrendPointApi {
  category: string
  count: number
}

export interface RegionTrendPointApi {
  region: string
  count: number
}

export interface SentimentTrendPointApi {
  date: string
  averageScore: number
  labelCounts: Record<string, number>
}

export interface UrgencyTrendPointApi {
  urgency: string
  count: number
}

export interface AnalyticsApiResponse {
  period: string
  volumeTrend: VolumeTrendPointApi[]
  categoryTrend: CategoryTrendPointApi[]
  regionTrend: RegionTrendPointApi[]
  sentimentTrend: SentimentTrendPointApi[]
  urgencyTrend: UrgencyTrendPointApi[]
  warnings: string[]
}
