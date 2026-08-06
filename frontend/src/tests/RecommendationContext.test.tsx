import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import { RecommendationContextProvider, useRecommendationContext } from '@/workspaces/recommendations/context'

function ContextProbe() {
  const context = useRecommendationContext()
  const { recommendationId, incidentId, activeSection, expandedSections, setActiveSection, toggleSectionExpanded } = context
  return (
    <div>
      <span data-testid="recommendationId">{recommendationId ?? 'none'}</span>
      <span data-testid="incidentId">{incidentId ?? 'none'}</span>
      <span data-testid="activeSection">{activeSection}</span>
      <span data-testid="expanded">{expandedSections.has('risk-assessment') ? 'expanded' : 'collapsed'}</span>
      <span data-testid="hasLifecycleField">{'lifecycleStage' in context ? 'yes' : 'no'}</span>
      <button type="button" onClick={() => setActiveSection('decision')}>
        Go to Decision
      </button>
      <button type="button" onClick={() => toggleSectionExpanded('risk-assessment')}>
        Toggle risk expansion
      </button>
    </div>
  )
}

describe('RecommendationContext', () => {
  it('throws when consumed outside a RecommendationContextProvider', () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
    expect(() => render(<ContextProbe />)).toThrow(/RecommendationContextProvider/)
    consoleError.mockRestore()
  })

  it('defaults to no reference ids and the Overview section active', () => {
    render(
      <RecommendationContextProvider>
        <ContextProbe />
      </RecommendationContextProvider>,
    )

    expect(screen.getByTestId('recommendationId')).toHaveTextContent('none')
    expect(screen.getByTestId('incidentId')).toHaveTextContent('none')
    expect(screen.getByTestId('activeSection')).toHaveTextContent('overview')
    expect(screen.getByTestId('expanded')).toHaveTextContent('collapsed')
  })

  it('accepts recommendationId and incidentId as references only -- never an investigationId', () => {
    render(
      <RecommendationContextProvider recommendationId="rec-1" incidentId="incident-1">
        <ContextProbe />
      </RecommendationContextProvider>,
    )

    expect(screen.getByTestId('recommendationId')).toHaveTextContent('rec-1')
    expect(screen.getByTestId('incidentId')).toHaveTextContent('incident-1')
    // Business data (the recommendation's real lifecycle stage) is deliberately absent from this
    // presentation-only Context -- it comes from real data in a future step, not local UI state.
    expect(screen.getByTestId('hasLifecycleField')).toHaveTextContent('no')
  })

  it('updates active section and expansion independently', async () => {
    const user = userEvent.setup()
    render(
      <RecommendationContextProvider>
        <ContextProbe />
      </RecommendationContextProvider>,
    )

    await user.click(screen.getByRole('button', { name: 'Go to Decision' }))
    expect(screen.getByTestId('activeSection')).toHaveTextContent('decision')

    await user.click(screen.getByRole('button', { name: 'Toggle risk expansion' }))
    expect(screen.getByTestId('expanded')).toHaveTextContent('expanded')
  })
})
