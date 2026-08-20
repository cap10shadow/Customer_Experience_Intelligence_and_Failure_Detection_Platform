import type { ReactNode } from 'react'
import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'

import { AnalyticsContextProvider } from '@/workspaces/analytics/context'
import { ExecutiveOverview } from '@/workspaces/analytics/components/ExecutiveOverview'
import { TrendAnalysis } from '@/workspaces/analytics/components/TrendAnalysis'
import { PatternDiscovery } from '@/workspaces/analytics/components/PatternDiscovery'
import { RecommendationEffectiveness } from '@/workspaces/analytics/components/RecommendationEffectiveness'
import { OrganizationalInsights } from '@/workspaces/analytics/components/OrganizationalInsights'
import { StrategicOpportunities } from '@/workspaces/analytics/components/StrategicOpportunities'

function withProviders(children: ReactNode) {
  return (
    <MemoryRouter>
      <AnalyticsContextProvider>{children}</AnalyticsContextProvider>
    </MemoryRouter>
  )
}

/**
 * Mirrors DashboardSections.test.tsx and RecommendationSections.test.tsx:
 * every section is rendered directly with `isLoading` and asserted to
 * suppress its real content and announce a busy region -- exercising
 * the real Section -> Card component hierarchy for each of the six
 * sections independently, not just the leaf `AnalyticsLoadingState`
 * primitive in isolation.
 */
describe('Section-level loading (real component hierarchy)', () => {
  it('Executive Overview suppresses real content and announces busy regions while loading', () => {
    render(withProviders(<ExecutiveOverview isLoading />))
    expect(screen.queryByText('Complaint volume')).not.toBeInTheDocument()
    expect(document.querySelectorAll('[aria-busy="true"]').length).toBe(3)
  })

  it('Executive Overview renders real, factual observations built from real trend data (Step 7.X A-08)', () => {
    const trends = [
      { id: 'category-trend', trend: 'billing recorded 18 complaint(s) in the returned trend data.', narrative: 'n', evidence: 'e' },
    ]
    render(withProviders(<ExecutiveOverview trends={trends} />))
    expect(screen.getByText('Complaint categories')).toBeInTheDocument()
    expect(screen.getByText('billing recorded 18 complaint(s) in the returned trend data.')).toBeInTheDocument()
  })

  it('Executive Overview renders an honest empty state when no trend data is returned', () => {
    render(withProviders(<ExecutiveOverview trends={[]} />))
    expect(screen.getByText('No observations available')).toBeInTheDocument()
    expect(screen.queryByText(/no data/i)).not.toBeInTheDocument()
  })

  it('Trend Analysis suppresses trend narratives while loading', () => {
    render(withProviders(<TrendAnalysis isLoading />))
    expect(screen.queryByText('Complaint volume has remained broadly stable across the period')).not.toBeInTheDocument()
    // Two narrative cards plus the supporting-charts panel, which now
    // shares the section's one loading state rather than popping in
    // after the narratives have already resolved.
    expect(document.querySelectorAll('[aria-busy="true"]').length).toBe(3)
  })

  it('Trend Analysis draws no chart at all when the section has no real returned series', () => {
    // The illustrative default narratives carry no data behind them. A
    // chart must only ever be drawn from values the backend actually
    // returned, so this state renders none -- never an empty axis, which
    // would read as a measured zero.
    render(withProviders(<TrendAnalysis />))
    expect(screen.queryByText('Supporting charts')).not.toBeInTheDocument()
    expect(document.querySelector('svg[role="img"]')).toBeNull()
  })

  it('Trend Analysis draws every returned series, and only from the values the Gateway returned', () => {
    render(
      withProviders(
        <TrendAnalysis
          trends={[{ id: 'complaint-volume-trend', trend: 'A', narrative: 'B', evidence: 'C' }]}
          series={{
            volume: [
              { date: '2026-08-15', count: 30 },
              { date: '2026-08-16', count: 4 },
            ],
            category: [{ category: 'delivery_issue', count: 49 }],
            region: [{ region: 'US-West', count: 35 }],
            sentiment: [{ date: '2026-08-16', averageScore: -1, labelCounts: { negative: 5 } }],
            urgency: [{ urgency: 'critical', count: 44 }],
          }}
        />,
      ),
    )

    expect(screen.getByText('Supporting charts')).toBeInTheDocument()
    expect(screen.getByRole('img', { name: 'Complaint volume per day' })).toBeInTheDocument()
    expect(screen.getByRole('img', { name: 'Average sentiment score per day' })).toBeInTheDocument()
    expect(screen.getByRole('list', { name: 'Complaint count by category' })).toBeInTheDocument()
    expect(screen.getByRole('list', { name: 'Complaint count by region' })).toBeInTheDocument()
    expect(screen.getByRole('list', { name: 'Complaint count by urgency' })).toBeInTheDocument()

    // Every charted value is also readable as text (beside its bar and
    // again in the chart's data table), so the geometry is never the
    // only record of a number the platform asserts.
    expect(screen.getAllByText('49').length).toBeGreaterThan(0)
    expect(screen.getAllByText('35').length).toBeGreaterThan(0)
    expect(screen.getAllByText('44').length).toBeGreaterThan(0)
    expect(screen.getAllByText('View as data')).toHaveLength(5)
  })

  it('Trend Analysis omits a chart for a series the Gateway returned empty, rather than drawing an empty axis', () => {
    render(
      withProviders(
        <TrendAnalysis
          trends={[{ id: 'complaint-volume-trend', trend: 'A', narrative: 'B', evidence: 'C' }]}
          series={{
            volume: [{ date: '2026-08-16', count: 4 }],
            category: [],
            region: [],
            sentiment: [],
            urgency: [],
          }}
        />,
      ),
    )

    expect(screen.getByRole('img', { name: 'Complaint volume per day' })).toBeInTheDocument()
    expect(screen.queryByRole('img', { name: 'Average sentiment score per day' })).not.toBeInTheDocument()
    expect(screen.queryByRole('list', { name: 'Complaint count by category' })).not.toBeInTheDocument()
  })

  it('Pattern Discovery suppresses the future-capability copy while loading, inside the same panel container both states share (Step 7.X G-02)', () => {
    const { container: loadingContainer } = render(withProviders(<PatternDiscovery isLoading />))
    expect(screen.queryByText('Pattern discovery is a future capability')).not.toBeInTheDocument()
    const loadingPanel = loadingContainer.querySelector('[aria-busy="true"]')?.parentElement
    expect(loadingPanel).not.toBeNull()
    expect(loadingPanel?.children).toHaveLength(1)

    render(withProviders(<PatternDiscovery />))
    expect(screen.getAllByText('Pattern discovery is a future capability')).toHaveLength(1)
    expect(screen.queryByText('Checkout-related complaints tend to recur around provider changes')).not.toBeInTheDocument()
  })

  it('Recommendation Effectiveness suppresses the future-capability copy while loading, inside the same panel container both states share', () => {
    const { container: loadingContainer } = render(withProviders(<RecommendationEffectiveness isLoading />))
    expect(screen.queryByText('Recommendation effectiveness is a future capability')).not.toBeInTheDocument()
    const loadingPanel = loadingContainer.querySelector('[aria-busy="true"]')?.parentElement
    expect(loadingPanel).not.toBeNull()
    expect(loadingPanel?.children).toHaveLength(1)

    render(withProviders(<RecommendationEffectiveness />))
    expect(screen.getAllByText('Recommendation effectiveness is a future capability')).toHaveLength(1)
  })

  it('Organizational Insights suppresses the future-capability copy while loading (Step 7.X G-02)', () => {
    render(withProviders(<OrganizationalInsights isLoading />))
    expect(screen.queryByText('Organizational insights are a future capability')).not.toBeInTheDocument()
    expect(document.querySelectorAll('[aria-busy="true"]').length).toBe(1)

    render(withProviders(<OrganizationalInsights />))
    expect(screen.getAllByText('Organizational insights are a future capability')).toHaveLength(1)
    expect(screen.queryByText(/Payment provider changes are a recurring precursor/)).not.toBeInTheDocument()
  })

  it('Strategic Opportunities suppresses the future-capability copy while loading (Step 7.X G-02)', () => {
    render(withProviders(<StrategicOpportunities isLoading />))
    expect(screen.queryByText('Strategic opportunity identification is a future capability')).not.toBeInTheDocument()
    expect(document.querySelectorAll('[aria-busy="true"]').length).toBe(1)

    render(withProviders(<StrategicOpportunities />))
    expect(screen.getAllByText('Strategic opportunity identification is a future capability')).toHaveLength(1)
    expect(screen.queryByText('Review how payment provider changes are communicated internally')).not.toBeInTheDocument()
  })
})
