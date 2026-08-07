import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import { AnalyticsContextProvider, useAnalyticsContext } from '@/workspaces/analytics/context'

function ContextProbe() {
  const context = useAnalyticsContext()
  const { selectedAnalysisPeriod, activeSection, expandedSections, selectedInsightId, setAnalysisPeriod, setActiveSection, toggleSectionExpanded, selectInsight } =
    context
  return (
    <div>
      <span data-testid="period">{selectedAnalysisPeriod}</span>
      <span data-testid="activeSection">{activeSection}</span>
      <span data-testid="expanded">{expandedSections.has('pattern-discovery') ? 'expanded' : 'collapsed'}</span>
      <span data-testid="selectedInsight">{selectedInsightId ?? 'none'}</span>
      <span data-testid="hasMetricsField">{'metrics' in context ? 'yes' : 'no'}</span>
      <button type="button" onClick={() => setAnalysisPeriod('last-quarter')}>
        Set last quarter
      </button>
      <button type="button" onClick={() => setActiveSection('organizational-insights')}>
        Go to Organizational Insights
      </button>
      <button type="button" onClick={() => toggleSectionExpanded('pattern-discovery')}>
        Toggle pattern expansion
      </button>
      <button type="button" onClick={() => selectInsight('insight-1')}>
        Select insight
      </button>
    </div>
  )
}

describe('AnalyticsContext', () => {
  it('throws when consumed outside an AnalyticsContextProvider', () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
    expect(() => render(<ContextProbe />)).toThrow(/AnalyticsContextProvider/)
    consoleError.mockRestore()
  })

  it('defaults to "last 30 days," the Executive Overview section active, and no selected insight', () => {
    render(
      <AnalyticsContextProvider>
        <ContextProbe />
      </AnalyticsContextProvider>,
    )

    expect(screen.getByTestId('period')).toHaveTextContent('last-30-days')
    expect(screen.getByTestId('activeSection')).toHaveTextContent('executive-overview')
    expect(screen.getByTestId('expanded')).toHaveTextContent('collapsed')
    expect(screen.getByTestId('selectedInsight')).toHaveTextContent('none')
    // Business data (real metrics/trend calculations) is deliberately absent from this
    // presentation-only Context, matching Dashboard/Investigation/Recommendation precedent.
    expect(screen.getByTestId('hasMetricsField')).toHaveTextContent('no')
  })

  it('updates analysis period, active section, expansion, and selected insight independently', async () => {
    const user = userEvent.setup()
    render(
      <AnalyticsContextProvider>
        <ContextProbe />
      </AnalyticsContextProvider>,
    )

    await user.click(screen.getByRole('button', { name: 'Set last quarter' }))
    expect(screen.getByTestId('period')).toHaveTextContent('last-quarter')

    await user.click(screen.getByRole('button', { name: 'Go to Organizational Insights' }))
    expect(screen.getByTestId('activeSection')).toHaveTextContent('organizational-insights')

    await user.click(screen.getByRole('button', { name: 'Toggle pattern expansion' }))
    expect(screen.getByTestId('expanded')).toHaveTextContent('expanded')

    await user.click(screen.getByRole('button', { name: 'Select insight' }))
    expect(screen.getByTestId('selectedInsight')).toHaveTextContent('insight-1')
  })
})
