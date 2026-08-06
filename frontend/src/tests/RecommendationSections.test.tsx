import type { ReactNode } from 'react'
import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'

import { RecommendationContextProvider } from '@/workspaces/recommendations/context'
import { RecommendationOverview } from '@/workspaces/recommendations/components/Overview'
import { RecommendationRationale } from '@/workspaces/recommendations/components/Rationale'
import { AlternativeOptions } from '@/workspaces/recommendations/components/AlternativeOptions'
import { ExpectedOutcome } from '@/workspaces/recommendations/components/ExpectedOutcome'
import { RiskAssessment } from '@/workspaces/recommendations/components/RiskAssessment'
import { Decision } from '@/workspaces/recommendations/components/Decision'
import { RecommendationLifecycle } from '@/workspaces/recommendations/components/RecommendationLifecycle'
import type { DecisionRecord } from '@/workspaces/recommendations/types'

const PENDING_DECISION: DecisionRecord = { status: 'pending-review', note: 'Awaiting review.' }
const APPROVED_DECISION: DecisionRecord = { status: 'approved', note: 'Approved.' }

function withProviders(children: ReactNode) {
  return (
    <MemoryRouter>
      <RecommendationContextProvider>{children}</RecommendationContextProvider>
    </MemoryRouter>
  )
}

/**
 * Mirrors DashboardSections.test.tsx (Phase 10 Step 2's rectification):
 * every section is rendered directly with `isLoading` and asserted to
 * suppress its real content and announce a busy region -- exercising
 * the real Section -> Card component hierarchy, not just the leaf
 * `RecommendationLoadingState` primitive in isolation.
 */
describe('Section-level loading (real component hierarchy)', () => {
  it('Recommendation Overview suppresses real content and announces busy while loading', () => {
    render(withProviders(<RecommendationOverview isLoading />))
    expect(screen.queryByText('Review the recent payment provider change')).not.toBeInTheDocument()
    expect(document.querySelectorAll('[aria-busy="true"]').length).toBeGreaterThan(0)
  })

  it('Recommendation Rationale suppresses content and the Traceability link while loading', () => {
    render(withProviders(<RecommendationRationale isLoading />))
    expect(screen.queryByText('The timing lines up with a known change')).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /Review the full investigation/ })).not.toBeInTheDocument()
    expect(document.querySelectorAll('[aria-busy="true"]').length).toBeGreaterThan(0)
  })

  it('Alternative Options suppresses the future-capability copy while loading, inside the same panel container both states share', () => {
    const { container: loadingContainer } = render(withProviders(<AlternativeOptions isLoading />))
    expect(screen.queryByText('Alternative option comparison is a future capability')).not.toBeInTheDocument()
    const loadingPanel = loadingContainer.querySelector('[aria-busy="true"]')?.parentElement
    expect(loadingPanel).not.toBeNull()
    // The loading branch renders as the sole child of the panel container --
    // not a sibling or a differently-shaped wrapper.
    expect(loadingPanel?.children).toHaveLength(1)

    const { container: loadedContainer } = render(withProviders(<AlternativeOptions />))
    const loadedPanel = loadedContainer.querySelector('[aria-busy]') // none while loaded
    expect(loadedPanel).toBeNull()
    expect(screen.getAllByText('Alternative option comparison is a future capability')).toHaveLength(1)
  })

  it('Expected Outcome suppresses all outcome cards and announces four independent busy regions while loading', () => {
    render(withProviders(<ExpectedOutcome isLoading />))
    expect(screen.queryByText('Operational improvement')).not.toBeInTheDocument()
    expect(document.querySelectorAll('[aria-busy="true"]').length).toBe(4)
  })

  it('Risk Assessment suppresses all risk cards while loading', () => {
    render(withProviders(<RiskAssessment isLoading />))
    expect(screen.queryByText('Trade-offs')).not.toBeInTheDocument()
    expect(document.querySelectorAll('[aria-busy="true"]').length).toBe(4)
  })

  it('Decision suppresses the decision status while loading', () => {
    render(withProviders(<Decision decision={PENDING_DECISION} isLoading />))
    expect(screen.queryByText('Pending Review')).not.toBeInTheDocument()
    expect(document.querySelectorAll('[aria-busy="true"]').length).toBeGreaterThan(0)
  })

  it('Recommendation Lifecycle suppresses stage progression while loading, even when Approved', () => {
    render(withProviders(<RecommendationLifecycle decision={APPROVED_DECISION} currentStage="awaiting-implementation" isLoading />))
    expect(screen.queryByText('Awaiting Implementation')).not.toBeInTheDocument()
    expect(document.querySelectorAll('[aria-busy="true"]').length).toBeGreaterThan(0)
  })
})
