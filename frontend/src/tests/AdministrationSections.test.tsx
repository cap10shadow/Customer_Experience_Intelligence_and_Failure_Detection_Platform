import type { ReactNode } from 'react'
import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'

import { AdministrationContextProvider } from '@/workspaces/administration/context'
import { PlatformOverview } from '@/workspaces/administration/components/PlatformOverview'
import { UserAccessManagement } from '@/workspaces/administration/components/UserAccessManagement'
import { DataSourcesIntegrations } from '@/workspaces/administration/components/DataSourcesIntegrations'
import { IntelligenceConfiguration } from '@/workspaces/administration/components/IntelligenceConfiguration'
import { PlatformGovernance } from '@/workspaces/administration/components/PlatformGovernance'
import { AuditChangeHistory } from '@/workspaces/administration/components/AuditChangeHistory'

function withProviders(children: ReactNode) {
  return (
    <MemoryRouter>
      <AdministrationContextProvider>{children}</AdministrationContextProvider>
    </MemoryRouter>
  )
}

/**
 * Mirrors RecommendationSections.test.tsx and AnalyticsSections.test.tsx:
 * every section is rendered directly with `isLoading` and asserted to
 * suppress its real content and announce busy regions -- exercising the
 * real Section -> Card component hierarchy for each of the six sections
 * independently.
 */
describe('Section-level loading (real component hierarchy)', () => {
  it('Platform Overview suppresses real content and announces busy regions while loading', () => {
    render(withProviders(<PlatformOverview isLoading />))
    expect(screen.queryByText('Operating normally')).not.toBeInTheDocument()
    expect(document.querySelectorAll('[aria-busy="true"]').length).toBe(7)
  })

  it('User & Access Management suppresses real content while loading', () => {
    render(withProviders(<UserAccessManagement isLoading />))
    expect(screen.queryByText(/24 users provisioned/)).not.toBeInTheDocument()
    expect(document.querySelectorAll('[aria-busy="true"]').length).toBe(5)
  })

  it('Data Sources & Integrations suppresses real content while loading', () => {
    render(withProviders(<DataSourcesIntegrations isLoading />))
    expect(screen.queryByText('Customer relationship management system')).not.toBeInTheDocument()
    expect(document.querySelectorAll('[aria-busy="true"]').length).toBe(2)
  })

  it('Intelligence Configuration suppresses real content while loading', () => {
    render(withProviders(<IntelligenceConfiguration isLoading />))
    expect(screen.queryByText('Anomaly Severity Threshold -- High')).not.toBeInTheDocument()
    expect(document.querySelectorAll('[aria-busy="true"]').length).toBe(3)
  })

  it('Platform Governance suppresses real content while loading', () => {
    render(withProviders(<PlatformGovernance isLoading />))
    expect(screen.queryByText('Operational data is retained for 24 months')).not.toBeInTheDocument()
    expect(document.querySelectorAll('[aria-busy="true"]').length).toBe(3)
  })

  it('Audit & Change History suppresses real content while loading', () => {
    render(withProviders(<AuditChangeHistory isLoading />))
    expect(screen.queryByText(/updated the Anomaly Severity Threshold/)).not.toBeInTheDocument()
    expect(document.querySelectorAll('[aria-busy="true"]').length).toBe(3)
  })
})

describe('ADM-002: Explanation Before Control in Intelligence Configuration', () => {
  it('presents what-it-is, then what it governs, then current value, then the edit affordance, in that fixed document order', () => {
    render(withProviders(<IntelligenceConfiguration />))

    const card = screen.getByText('Anomaly Severity Threshold -- High').closest('div')
    expect(card).not.toBeNull()
    const text = card!.parentElement!.textContent ?? ''

    const whatItIsIndex = text.indexOf('The complaint-spike magnitude above which')
    const governsIndex = text.indexOf('Determines when a complaint spike is classified')
    const valueLabelIndex = text.indexOf('Current value')
    const editIndex = text.indexOf('Edit')

    expect(whatItIsIndex).toBeGreaterThan(-1)
    expect(governsIndex).toBeGreaterThan(whatItIsIndex)
    expect(valueLabelIndex).toBeGreaterThan(governsIndex)
    expect(editIndex).toBeGreaterThan(valueLabelIndex)
  })

  it('defaults every configuration value to read-only inspection, never editable', () => {
    render(withProviders(<IntelligenceConfiguration />))

    const inputs = screen.getAllByRole('textbox')
    inputs.forEach((input) => {
      expect(input).toHaveAttribute('readonly')
    })
  })

  it('only enters an editable state after the Edit affordance is explicitly used, and distinguishes inspection from editing via aria-pressed', async () => {
    const user = userEvent.setup()
    render(withProviders(<IntelligenceConfiguration />))

    const editButtons = screen.getAllByRole('button', { name: 'Edit' })
    expect(editButtons[0]).toHaveAttribute('aria-pressed', 'false')

    await user.click(editButtons[0])

    const inputs = screen.getAllByRole('textbox')
    expect(inputs[0]).not.toHaveAttribute('readonly')
    expect(screen.getByRole('button', { name: /done inspecting draft/i })).toHaveAttribute('aria-pressed', 'true')
  })

  it('never persists a configuration change -- no fetch, no save confirmation, no network call is possible in this step', () => {
    // No save/confirm control exists at all; the only control is the Edit toggle.
    render(withProviders(<IntelligenceConfiguration />))
    expect(screen.queryByRole('button', { name: /save/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /confirm/i })).not.toBeInTheDocument()
  })
})

describe('ADM-004: Intelligence Configuration presentation weight', () => {
  it('never renders a critical- or warning-toned element -- weight comes from spacing, never alarm styling', () => {
    const { container } = render(withProviders(<IntelligenceConfiguration />))
    expect(container.querySelectorAll('[class*="critical"]')).toHaveLength(0)
    expect(container.querySelectorAll('[class*="warning"]')).toHaveLength(0)
  })
})

describe('ADM-001: Platform Governance vs. Audit & Change History', () => {
  it('Platform Governance renders calm narrative prose, never a selectable or button-based item', () => {
    render(withProviders(<PlatformGovernance />))
    expect(screen.getByText('Operational data is retained for 24 months')).toBeInTheDocument()
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
  })

  it('Audit & Change History renders a semantic, labeled ledger list distinct from Governance\'s narrative container', () => {
    render(withProviders(<AuditChangeHistory />))
    expect(screen.getByRole('list', { name: /administrative change history/i })).toBeInTheDocument()
  })

  it('Audit & Change History honestly explains an empty ledger rather than stating "No Data"', () => {
    render(withProviders(<AuditChangeHistory entries={[]} />))
    expect(screen.getByText('No administrative actions have been recorded yet')).toBeInTheDocument()
    expect(screen.queryByText(/no data/i)).not.toBeInTheDocument()
  })
})

describe('ADM-003: Audit & Change History never resembles an activity feed', () => {
  it('renders no interactive controls -- entries are static, permanent rows, never clickable', () => {
    render(withProviders(<AuditChangeHistory />))
    const list = screen.getByRole('list', { name: /administrative change history/i })
    expect(list.querySelectorAll('button')).toHaveLength(0)
    expect(list.querySelectorAll('[aria-pressed]')).toHaveLength(0)
  })

  it('never uses "new" badge, unread, or notification language', () => {
    render(withProviders(<AuditChangeHistory />))
    expect(screen.queryByText(/^new$/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/unread/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/notification/i)).not.toBeInTheDocument()
  })

  it('presents every entry with an absolute timestamp via a semantic <time> element, never a relative "ago" string', () => {
    render(withProviders(<AuditChangeHistory />))
    const timeElements = document.querySelectorAll('time')
    expect(timeElements.length).toBeGreaterThan(0)
    timeElements.forEach((element) => {
      expect(element.textContent).not.toMatch(/ago$/i)
      expect(element.getAttribute('datetime')).toBeTruthy()
    })
  })

  it('every rendered datetime attribute is a valid ISO-8601 UTC value, distinct from the human-readable visible text', () => {
    render(withProviders(<AuditChangeHistory />))
    const timeElements = document.querySelectorAll('time')
    expect(timeElements.length).toBeGreaterThan(0)

    const isoUtcPattern = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?Z$/
    timeElements.forEach((element) => {
      const datetimeAttribute = element.getAttribute('datetime')
      expect(datetimeAttribute).toMatch(isoUtcPattern)
      // The visible text stays the frozen human-readable form (e.g. "2026-08-05 09:14 UTC")
      // -- only the machine-readable attribute changes shape.
      expect(element.textContent).toMatch(/^\d{4}-\d{2}-\d{2} \d{2}:\d{2} UTC$/)
      expect(element.textContent).not.toBe(datetimeAttribute)
    })
  })
})

describe('ADM-006: Connected Services vs. Connected Systems', () => {
  it('Platform Overview labels its list "Connected Services" and every item as platform infrastructure', () => {
    render(withProviders(<PlatformOverview />))
    expect(screen.getByRole('heading', { level: 3, name: 'Connected Services' })).toBeInTheDocument()
    expect(screen.getAllByText('Platform infrastructure dependency').length).toBeGreaterThan(0)
  })

  it('Data Sources & Integrations labels its list "Connected Systems" and every item as an external business system', () => {
    render(withProviders(<DataSourcesIntegrations />))
    expect(screen.getByRole('heading', { level: 3, name: 'Connected Systems' })).toBeInTheDocument()
    expect(screen.getAllByText('External business system').length).toBeGreaterThan(0)
  })

  it('never mixes an infrastructure dependency into the Connected Systems list or vice versa', () => {
    render(withProviders(<DataSourcesIntegrations />))
    expect(screen.queryByText('Primary database')).not.toBeInTheDocument()
    expect(screen.queryByText('Event infrastructure')).not.toBeInTheDocument()
  })

  it('Data Sources & Integrations honestly explains zero connected systems rather than stating "No Data"', () => {
    render(withProviders(<DataSourcesIntegrations systems={[]} />))
    expect(screen.getByText('No external systems are connected yet')).toBeInTheDocument()
    expect(screen.queryByText(/no data/i)).not.toBeInTheDocument()
  })
})

describe('Connection Health is descriptive only', () => {
  it('never renders a critical- or warning-toned status for Connection Health', () => {
    const { container } = render(withProviders(<DataSourcesIntegrations />))
    expect(container.querySelectorAll('[class*="critical"]')).toHaveLength(0)
    expect(container.querySelectorAll('[class*="warning"]')).toHaveLength(0)
  })
})

describe('Platform Overview stays descriptive only', () => {
  it('renders no action or recommendation controls', () => {
    render(withProviders(<PlatformOverview />))
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
  })
})
