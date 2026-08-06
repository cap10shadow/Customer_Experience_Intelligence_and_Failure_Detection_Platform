import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import { InvestigationContextProvider, useInvestigationContext } from '@/workspaces/investigations/context'

function ContextProbe() {
  const { incidentId, activeSection, expandedSections, selectedEvidenceId, setActiveSection, toggleSectionExpanded, selectEvidence } =
    useInvestigationContext()
  return (
    <div>
      <span data-testid="incidentId">{incidentId ?? 'none'}</span>
      <span data-testid="activeSection">{activeSection}</span>
      <span data-testid="expanded">{expandedSections.has('evidence') ? 'expanded' : 'collapsed'}</span>
      <span data-testid="selectedEvidence">{selectedEvidenceId ?? 'none'}</span>
      <button type="button" onClick={() => setActiveSection('business-impact')}>
        Go to Business Impact
      </button>
      <button type="button" onClick={() => toggleSectionExpanded('evidence')}>
        Toggle evidence expansion
      </button>
      <button type="button" onClick={() => selectEvidence('evidence-1')}>
        Select evidence
      </button>
    </div>
  )
}

describe('InvestigationContext', () => {
  it('throws when consumed outside an InvestigationContextProvider', () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
    expect(() => render(<ContextProbe />)).toThrow(/InvestigationContextProvider/)
    consoleError.mockRestore()
  })

  it('defaults to no Incident reference and the Observation section active', () => {
    render(
      <InvestigationContextProvider>
        <ContextProbe />
      </InvestigationContextProvider>,
    )

    expect(screen.getByTestId('incidentId')).toHaveTextContent('none')
    expect(screen.getByTestId('activeSection')).toHaveTextContent('observation')
    expect(screen.getByTestId('expanded')).toHaveTextContent('collapsed')
    expect(screen.getByTestId('selectedEvidence')).toHaveTextContent('none')
  })

  it('accepts an incidentId -- Investigation only ever references an Incident, never owns one', () => {
    render(
      <InvestigationContextProvider incidentId="incident-42">
        <ContextProbe />
      </InvestigationContextProvider>,
    )

    expect(screen.getByTestId('incidentId')).toHaveTextContent('incident-42')
  })

  it('updates active section, expansion, and selected evidence independently', async () => {
    const user = userEvent.setup()
    render(
      <InvestigationContextProvider>
        <ContextProbe />
      </InvestigationContextProvider>,
    )

    await user.click(screen.getByRole('button', { name: 'Go to Business Impact' }))
    expect(screen.getByTestId('activeSection')).toHaveTextContent('business-impact')

    await user.click(screen.getByRole('button', { name: 'Toggle evidence expansion' }))
    expect(screen.getByTestId('expanded')).toHaveTextContent('expanded')

    await user.click(screen.getByRole('button', { name: 'Select evidence' }))
    expect(screen.getByTestId('selectedEvidence')).toHaveTextContent('evidence-1')
  })
})
