import type { ReactNode } from 'react'
import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'

import { AdministrationContextProvider } from '@/workspaces/administration/context'
import { PlatformOverview } from '@/workspaces/administration/components/PlatformOverview'
import { UserAccessManagement } from '@/workspaces/administration/components/UserAccessManagement'
import { DataSourcesIntegrations } from '@/workspaces/administration/components/DataSourcesIntegrations'
import { IntelligenceConfiguration } from '@/workspaces/administration/components/IntelligenceConfiguration'
import { PlatformGovernance } from '@/workspaces/administration/components/PlatformGovernance'
import { AuditChangeHistory } from '@/workspaces/administration/components/AuditChangeHistory'
import type { ConfigurationItem } from '@/workspaces/administration/types'

function withProviders(children: ReactNode) {
  return (
    <MemoryRouter>
      <AdministrationContextProvider>{children}</AdministrationContextProvider>
    </MemoryRouter>
  )
}

const SAMPLE_CONFIGURATION_ITEMS: ConfigurationItem[] = [
  {
    id: 'business-impact-weight-financial',
    name: 'Financial Impact Weight',
    whatItIs: 'The relative weight this dimension carries in the overall weighted business impact score.',
    governs: 'Determines how much this dimension contributes to an Incident\'s overall business score.',
    currentValue: '35%',
  },
  {
    id: 'business-impact-severity-bands',
    name: 'Business Impact Severity Bands',
    whatItIs: 'The weighted-business-score thresholds that classify an Incident\'s overall severity.',
    governs: 'Determines which ImpactLevel an Incident\'s overall weighted business score is classified into.',
    currentValue: 'None ≤20, Low ≤40, Medium ≤60, High ≤80',
  },
]

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
    expect(screen.queryByText('9/9 services healthy')).not.toBeInTheDocument()
    // 5 Platform Overview facts + 9 service-health facts (Step 7.X A-02) + 2 Connected Services.
    expect(document.querySelectorAll('[aria-busy="true"]').length).toBe(16)
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
    expect(screen.queryByText('Financial Impact Weight')).not.toBeInTheDocument()
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

describe('Step 7.X G-05: real, read-only Intelligence Configuration', () => {
  it('presents what-it-is, then what it governs, then the current value, in that fixed document order, for real fetched items', () => {
    render(withProviders(<IntelligenceConfiguration items={SAMPLE_CONFIGURATION_ITEMS} />))

    const card = screen.getByText('Financial Impact Weight').closest('div')
    expect(card).not.toBeNull()
    const text = card!.parentElement!.textContent ?? ''

    const whatItIsIndex = text.indexOf('The relative weight this dimension carries')
    const governsIndex = text.indexOf('Determines how much this dimension contributes')
    const valueLabelIndex = text.indexOf('Current value')

    expect(whatItIsIndex).toBeGreaterThan(-1)
    expect(governsIndex).toBeGreaterThan(whatItIsIndex)
    expect(valueLabelIndex).toBeGreaterThan(governsIndex)
  })

  it('renders the real current value for every item, sourced from the fetched response, never a hardcoded copy', () => {
    render(withProviders(<IntelligenceConfiguration items={SAMPLE_CONFIGURATION_ITEMS} />))

    expect(screen.getByText('35%')).toBeInTheDocument()
    expect(screen.getByText('None ≤20, Low ≤40, Medium ≤60, High ≤80')).toBeInTheDocument()
  })

  it('never renders an edit button, save button, toggle, or any mutation control', async () => {
    render(withProviders(<IntelligenceConfiguration items={SAMPLE_CONFIGURATION_ITEMS} />))

    expect(screen.queryByRole('button', { name: /edit/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /save/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /confirm/i })).not.toBeInTheDocument()
    expect(screen.queryAllByRole('textbox')).toHaveLength(0)
  })

  it('shows an honest empty state, not a blank section, when the real response has no items', () => {
    render(withProviders(<IntelligenceConfiguration items={[]} />))

    expect(screen.getByText('No configuration values available')).toBeInTheDocument()
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
