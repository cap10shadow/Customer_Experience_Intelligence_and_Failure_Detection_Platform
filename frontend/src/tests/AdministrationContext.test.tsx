import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import { AdministrationContextProvider, useAdministrationContext } from '@/workspaces/administration/context'

function ContextProbe() {
  const context = useAdministrationContext()
  const { activeSection, expandedSections, selectedConfigurationId, setActiveSection, toggleSectionExpanded, selectConfigurationItem } =
    context
  return (
    <div>
      <span data-testid="activeSection">{activeSection}</span>
      <span data-testid="expanded">{expandedSections.has('intelligence-configuration') ? 'expanded' : 'collapsed'}</span>
      <span data-testid="selectedConfiguration">{selectedConfigurationId ?? 'none'}</span>
      <span data-testid="hasUsersField">{'users' in context ? 'yes' : 'no'}</span>
      <span data-testid="hasPoliciesField">{'policies' in context ? 'yes' : 'no'}</span>
      <span data-testid="hasAuditHistoryField">{'auditHistory' in context ? 'yes' : 'no'}</span>
      <button type="button" onClick={() => setActiveSection('audit-change-history')}>
        Go to Audit & Change History
      </button>
      <button type="button" onClick={() => toggleSectionExpanded('intelligence-configuration')}>
        Toggle configuration expansion
      </button>
      <button type="button" onClick={() => selectConfigurationItem('config-1')}>
        Select configuration item
      </button>
    </div>
  )
}

describe('AdministrationContext', () => {
  it('throws when consumed outside an AdministrationContextProvider', () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
    expect(() => render(<ContextProbe />)).toThrow(/AdministrationContextProvider/)
    consoleError.mockRestore()
  })

  it('defaults to Platform Overview active, nothing expanded, and no selected configuration item', () => {
    render(
      <AdministrationContextProvider>
        <ContextProbe />
      </AdministrationContextProvider>,
    )

    expect(screen.getByTestId('activeSection')).toHaveTextContent('platform-overview')
    expect(screen.getByTestId('expanded')).toHaveTextContent('collapsed')
    expect(screen.getByTestId('selectedConfiguration')).toHaveTextContent('none')
  })

  it('owns exactly activeSection, expandedSections, and selectedConfigurationId -- never users, roles, permissions, integrations, policies, audit history, or platform status', () => {
    render(
      <AdministrationContextProvider>
        <ContextProbe />
      </AdministrationContextProvider>,
    )

    expect(screen.getByTestId('hasUsersField')).toHaveTextContent('no')
    expect(screen.getByTestId('hasPoliciesField')).toHaveTextContent('no')
    expect(screen.getByTestId('hasAuditHistoryField')).toHaveTextContent('no')
  })

  it('updates active section, expansion, and selected configuration item independently', async () => {
    const user = userEvent.setup()
    render(
      <AdministrationContextProvider>
        <ContextProbe />
      </AdministrationContextProvider>,
    )

    await user.click(screen.getByRole('button', { name: 'Go to Audit & Change History' }))
    expect(screen.getByTestId('activeSection')).toHaveTextContent('audit-change-history')

    await user.click(screen.getByRole('button', { name: 'Toggle configuration expansion' }))
    expect(screen.getByTestId('expanded')).toHaveTextContent('expanded')

    await user.click(screen.getByRole('button', { name: 'Select configuration item' }))
    expect(screen.getByTestId('selectedConfiguration')).toHaveTextContent('config-1')
  })
})
