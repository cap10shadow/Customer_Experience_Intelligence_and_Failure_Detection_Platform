import type { ReactNode } from 'react'
import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'

import { DashboardContextProvider } from '@/workspaces/dashboard/context'
import { DashboardWorkspace } from '@/workspaces/dashboard'
import { OperationalBrief } from '@/workspaces/dashboard/components/OperationalBrief'
import { DecisionSummary } from '@/workspaces/dashboard/components/DecisionSummary'
import { InvestigationEntryPoints } from '@/workspaces/dashboard/components/InvestigationEntryPoints'
import { SupportingEvidence } from '@/workspaces/dashboard/components/SupportingEvidence'

function withProviders(children: ReactNode) {
  return (
    <MemoryRouter>
      <DashboardContextProvider>{children}</DashboardContextProvider>
    </MemoryRouter>
  )
}

describe('Operational Brief landmark structure', () => {
  it('exposes exactly the four top-level Dashboard section landmarks, not one per subsection', () => {
    render(
      <MemoryRouter>
        <DashboardWorkspace />
      </MemoryRouter>,
    )

    const regions = screen.getAllByRole('region')
    expect(regions).toHaveLength(4)
    expect(regions.map((region) => region.getAttribute('aria-labelledby')).every(Boolean)).toBe(true)
  })

  it('still exposes every Operational Brief subsection as a real, findable heading', () => {
    render(withProviders(<OperationalBrief />))

    ;['Overall operational status', 'Critical situations', 'Key changes', 'Recommended focus', 'Operational health snapshot'].forEach(
      (title) => {
        expect(screen.getByRole('heading', { level: 3, name: title })).toBeInTheDocument()
      },
    )
  })
})

describe('Section-level loading (real component hierarchy, not just the leaf primitive)', () => {
  it('Operational Brief suppresses real content and announces busy regions while loading', () => {
    render(withProviders(<OperationalBrief isLoading />))

    expect(screen.queryByText('Operations Stable')).not.toBeInTheDocument()
    expect(document.querySelectorAll('[aria-busy="true"]').length).toBeGreaterThan(0)
  })

  it('Decision Summary renders loading cards through DecisionOpportunityCard itself, not a duplicated skeleton', () => {
    render(withProviders(<DecisionSummary isLoading />))

    expect(screen.queryByRole('heading', { name: 'Approve recommendation' })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /Review recommendation/ })).not.toBeInTheDocument()
    // Card count while loading matches the real data count -- no hardcoded skeleton count.
    expect(document.querySelectorAll('article').length).toBe(2)
    expect(document.querySelectorAll('[aria-busy="true"]').length).toBe(2)
  })

  it('Investigation Entry Points renders loading cards through OperationalStoryCard itself', () => {
    render(withProviders(<InvestigationEntryPoints isLoading />))

    expect(screen.queryByRole('heading', { name: 'Payment reliability deteriorating' })).not.toBeInTheDocument()
    expect(document.querySelectorAll('article').length).toBe(2)
    expect(document.querySelectorAll('[aria-busy="true"]').length).toBe(2)
  })

  it('Supporting Evidence suppresses evidence content while loading', () => {
    render(withProviders(<SupportingEvidence isLoading />))

    expect(screen.queryByText('Operational trends')).not.toBeInTheDocument()
    expect(document.querySelectorAll('[aria-busy="true"]').length).toBe(5)
  })
})

describe('Section content is now injectable, so the empty-state branch is reachable', () => {
  it('Decision Summary shows a confident empty state when given zero opportunities', () => {
    render(withProviders(<DecisionSummary opportunities={[]} />))
    expect(screen.getByText('No decisions require attention')).toBeInTheDocument()
  })

  it('Investigation Entry Points shows a confident empty state when given zero stories', () => {
    render(withProviders(<InvestigationEntryPoints stories={[]} />))
    expect(screen.getByText('No operational stories currently need investigation')).toBeInTheDocument()
  })
})

describe('DashboardDrillDownLink reuse', () => {
  it('renders the drill-down affordance on a Decision Opportunity card', () => {
    render(withProviders(<DecisionSummary />))
    expect(screen.getByRole('link', { name: /Review recommendation/ })).toHaveAttribute('href', '/recommendations')
  })

  it('renders the same drill-down affordance on an Operational Story card', () => {
    render(withProviders(<InvestigationEntryPoints />))
    expect(screen.getByRole('link', { name: /Investigate this story/ })).toHaveAttribute('href', '/investigations')
  })
})
