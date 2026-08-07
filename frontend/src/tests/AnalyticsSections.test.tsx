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

  it('Trend Analysis suppresses trend narratives while loading', () => {
    render(withProviders(<TrendAnalysis isLoading />))
    expect(screen.queryByText('Complaint volume has remained broadly stable across the period')).not.toBeInTheDocument()
    expect(document.querySelectorAll('[aria-busy="true"]').length).toBe(2)
  })

  it('Pattern Discovery suppresses pattern narratives while loading', () => {
    render(withProviders(<PatternDiscovery isLoading />))
    expect(screen.queryByText('Checkout-related complaints tend to recur around provider changes')).not.toBeInTheDocument()
    expect(document.querySelectorAll('[aria-busy="true"]').length).toBe(1)
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

  it('Organizational Insights suppresses insight cards while loading', () => {
    render(withProviders(<OrganizationalInsights isLoading />))
    expect(screen.queryByText(/Payment provider changes are a recurring precursor/)).not.toBeInTheDocument()
    expect(document.querySelectorAll('[aria-busy="true"]').length).toBe(1)
  })

  it('Strategic Opportunities suppresses opportunity cards while loading', () => {
    render(withProviders(<StrategicOpportunities isLoading />))
    expect(screen.queryByText('Review how payment provider changes are communicated internally')).not.toBeInTheDocument()
    expect(document.querySelectorAll('[aria-busy="true"]').length).toBe(2)
  })
})
