import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'

import { AdministrationWorkspace } from '@/workspaces/administration'

const SAMPLE_ADMINISTRATION_RESPONSE = {
  services: [
    { id: 'gateway', name: 'Gateway Service', status: 'healthy', detail: 'ok' },
    { id: 'ingestion', name: 'Ingestion Service', status: 'healthy', detail: 'ok' },
    { id: 'nlp', name: 'NLP Service', status: 'healthy', detail: 'ok' },
    { id: 'anomaly', name: 'Anomaly Service', status: 'healthy', detail: 'ok' },
    { id: 'root_cause', name: 'Root Cause Service', status: 'healthy', detail: 'ok' },
    { id: 'business_impact', name: 'Business Impact Service', status: 'healthy', detail: 'ok' },
    { id: 'recommendation', name: 'Recommendation Service', status: 'healthy', detail: 'ok' },
    { id: 'copilot', name: 'Copilot Service', status: 'healthy', detail: 'ok' },
    { id: 'evaluation', name: 'Evaluation Service', status: 'healthy', detail: 'ok' },
  ],
  warnings: [],
}

const SAMPLE_INTELLIGENCE_CONFIGURATION_RESPONSE = {
  items: [
    {
      id: 'business-impact-weight-financial',
      name: 'Financial Impact Weight',
      whatItIs: 'The relative weight this dimension carries in the overall weighted business impact score.',
      governs: "Determines how much this dimension contributes to an Incident's overall business score.",
      currentValue: '35%',
    },
  ],
}

function jsonResponse(body: unknown, status = 200) {
  return { status, ok: status >= 200 && status < 300, text: async () => JSON.stringify(body) } as Response
}

function mockFetchByUrl() {
  return vi.fn((input: RequestInfo | URL) => {
    const url = String(input)
    if (url.includes('/administration/intelligence-configuration')) {
      return Promise.resolve(jsonResponse(SAMPLE_INTELLIGENCE_CONFIGURATION_RESPONSE))
    }
    return Promise.resolve(jsonResponse(SAMPLE_ADMINISTRATION_RESPONSE))
  })
}

function mountWorkspace() {
  return render(
    <MemoryRouter>
      <AdministrationWorkspace />
    </MemoryRouter>,
  )
}

/**
 * AdministrationWorkspace owns a real (if brief) initial loading state and
 * passes it through the composed section hierarchy -- so composition
 * assertions that need loaded content wait for that transition to
 * finish, exactly as Analytics' (Step 5) equivalent test does.
 */
async function renderWorkspace() {
  const utils = mountWorkspace()
  await waitFor(() => {
    expect(document.querySelectorAll('[aria-busy="true"]')).toHaveLength(0)
  })
  return utils
}

beforeEach(() => {
  vi.stubGlobal('fetch', mockFetchByUrl())
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('AdministrationWorkspace loading (real composition hierarchy)', () => {
  it('starts every section busy and transitions to loaded content once the workspace load completes, without a static isLoading prop', async () => {
    mountWorkspace()

    expect(document.querySelectorAll('[aria-busy="true"]').length).toBeGreaterThan(0)
    expect(screen.queryByText('9/9 services healthy')).not.toBeInTheDocument()

    await waitFor(() => {
      expect(document.querySelectorAll('[aria-busy="true"]')).toHaveLength(0)
    })

    expect(screen.getByText('9/9 services healthy')).toBeInTheDocument()
  })
})

describe('AdministrationWorkspace composition', () => {
  it('renders one workspace heading and the six sections in fixed order', async () => {
    await renderWorkspace()

    expect(screen.getByRole('heading', { level: 1, name: 'Administration' })).toBeInTheDocument()

    const sectionHeadings = screen.getAllByRole('heading', { level: 2 }).map((heading) => heading.textContent)
    expect(sectionHeadings).toEqual([
      'Platform Overview',
      'User & Access Management',
      'Data Sources & Integrations',
      'Intelligence Configuration',
      'Platform Governance',
      'Audit & Change History',
    ])
  })

  it('renders the persistent Administration Navigator with a link to every section, reusing the Investigation/Recommendation/Analytics navigator family', async () => {
    await renderWorkspace()

    expect(screen.getByRole('navigation', { name: 'Administration sections' })).toBeInTheDocument()
    ;[
      'Platform Overview',
      'User & Access Management',
      'Data Sources & Integrations',
      'Intelligence Configuration',
      'Platform Governance',
      'Audit & Change History',
    ].forEach((label) => {
      expect(screen.getByRole('link', { name: label })).toBeInTheDocument()
    })
  })

  it('marks the active section via aria-current when a navigator link is used', async () => {
    const user = userEvent.setup()
    await renderWorkspace()

    const overviewLink = screen.getByRole('link', { name: 'Platform Overview' })
    expect(overviewLink).toHaveAttribute('aria-current', 'true')

    const governanceLink = screen.getByRole('link', { name: 'Platform Governance' })
    await user.click(governanceLink)

    expect(governanceLink).toHaveAttribute('aria-current', 'true')
    expect(overviewLink).not.toHaveAttribute('aria-current')
  })

  it('never introduces tabs, a wizard, or grouped navigation -- a single flat navigator list only', async () => {
    await renderWorkspace()

    const nav = screen.getByRole('navigation', { name: 'Administration sections' })
    expect(nav.querySelectorAll('[role="tab"]')).toHaveLength(0)
    expect(nav.querySelectorAll('[role="tablist"]')).toHaveLength(0)
    expect(nav.querySelectorAll('ol')).toHaveLength(1)
  })
})

describe('Administration never participates in operational intelligence, monitoring, or workflow', () => {
  it('renders no incident management, recommendation approval, or workflow controls anywhere in the workspace', async () => {
    await renderWorkspace()

    expect(screen.queryByRole('button', { name: /approve/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /assign/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /reject/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /defer/i })).not.toBeInTheDocument()
  })

  it('never renders a dashboard-style status wall or live monitoring language', async () => {
    await renderWorkspace()

    expect(screen.queryByText(/live/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/real-time/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/monitoring/i)).not.toBeInTheDocument()
  })
})

describe('Regression protection for ADM-001 through ADM-006', () => {
  it('ADM-001: Platform Governance and Audit & Change History are adjacent but texturally distinct', async () => {
    await renderWorkspace()

    // Governance: calm narrative, no interactive list.
    const governanceHeading = screen.getByRole('heading', { level: 2, name: 'Platform Governance' })
    const governanceSection = governanceHeading.closest('section')
    expect(governanceSection?.querySelectorAll('button')).toHaveLength(0)
    expect(governanceSection?.querySelector('ol')).toBeNull()

    // Audit: a labeled, semantic ledger list.
    const auditHeading = screen.getByRole('heading', { level: 2, name: 'Audit & Change History' })
    const auditSection = auditHeading.closest('section')
    expect(auditSection?.querySelector('ol[aria-label]')).not.toBeNull()
  })

  it('Step 7.X G-05: Intelligence Configuration renders real, read-only values with no editable input anywhere', async () => {
    await renderWorkspace()

    const configurationHeading = screen.getByRole('heading', { level: 2, name: 'Intelligence Configuration' })
    const configurationSection = configurationHeading.closest('section')
    expect(configurationSection?.querySelectorAll('input')).toHaveLength(0)
    expect(configurationSection?.querySelectorAll('button')).toHaveLength(0)
    expect(screen.getByText('35%')).toBeInTheDocument()
  })

  it('ADM-003: Audit & Change History renders no clickable rows and no "new"/unread language', async () => {
    await renderWorkspace()

    const auditHeading = screen.getByRole('heading', { level: 2, name: 'Audit & Change History' })
    const auditSection = auditHeading.closest('section')
    expect(auditSection?.querySelectorAll('button')).toHaveLength(0)
    expect(auditSection?.querySelectorAll('[aria-pressed]')).toHaveLength(0)
    expect(auditSection?.textContent).not.toMatch(/\bunread\b/i)
  })

  it('ADM-004: Intelligence Configuration never renders alarm-toned elements anywhere in the workspace', async () => {
    const { container } = await renderWorkspace()

    expect(container.querySelectorAll('[class*="critical"]')).toHaveLength(0)
    expect(container.querySelectorAll('[class*="warning"]')).toHaveLength(0)
  })

  it('ADM-005: register rhythm is expressed as data attributes only, never a second navigation grouping', async () => {
    await renderWorkspace()

    // Each register's data attribute appears twice per section it covers --
    // once on the reading-column section wrapper, once on the matching
    // navigator link's <li> -- and nowhere else (no grouped <ol>, no
    // fieldset, no aria-labelledby grouping).
    expect(document.querySelectorAll('[data-register="state"]').length).toBe(6)
    expect(document.querySelectorAll('[data-register="configuration"]').length).toBe(2)
    expect(document.querySelectorAll('[data-register="record"]').length).toBe(4)
    expect(screen.getByRole('navigation', { name: 'Administration sections' }).querySelectorAll('ol')).toHaveLength(1)
  })

  it('ADM-006: Connected Services and Connected Systems are both present and never collapse into one list', async () => {
    await renderWorkspace()

    expect(screen.getByRole('heading', { level: 3, name: 'Connected Services' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { level: 3, name: 'Connected Systems' })).toBeInTheDocument()
  })
})
