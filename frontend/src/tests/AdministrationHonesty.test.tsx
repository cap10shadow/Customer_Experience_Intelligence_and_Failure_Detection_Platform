import type { ReactNode } from 'react'
import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'

import { AdministrationContextProvider } from '@/workspaces/administration/context'
import { AuditChangeHistory } from '@/workspaces/administration/components/AuditChangeHistory'
import { DataSourcesIntegrations } from '@/workspaces/administration/components/DataSourcesIntegrations'
import { PlatformGovernance } from '@/workspaces/administration/components/PlatformGovernance'
import { UserAccessManagement } from '@/workspaces/administration/components/UserAccessManagement'

function withProviders(children: ReactNode) {
  return (
    <MemoryRouter>
      <AdministrationContextProvider>{children}</AdministrationContextProvider>
    </MemoryRouter>
  )
}

/**
 * Four of Administration's six sections are presentation-only: no
 * Gateway route backs them, and every value they show is fixed example
 * copy. That was previously documented in each component's own source
 * comment and in the project's limitation list -- but nothing said so on
 * the rendered page. A user saw specific user counts, a named list of
 * "Connected" external systems, a retention policy, and an audit ledger
 * naming individual people at precise timestamps, with no indication
 * that none of it was real. Some of it also described capabilities the
 * platform does not have at all (single sign-on; this platform
 * authenticates with email and password).
 *
 * These tests assert the disclosure is *rendered*, not merely commented
 * -- the distinction the previous state got wrong.
 */
describe('Administration presentation-only sections disclose themselves on the page', () => {
  it('User & Access Management states that its access configuration is illustrative', () => {
    render(withProviders(<UserAccessManagement />))
    expect(screen.getByText(/Illustrative content/)).toBeInTheDocument()
    expect(screen.getByText(/no user or role administration capability yet/)).toBeInTheDocument()
  })

  it('corrects the single sign-on claim rather than leaving it as an unqualified statement of fact', () => {
    render(withProviders(<UserAccessManagement />))
    expect(screen.getByText(/signs in with email and password rather than single sign-on/)).toBeInTheDocument()
  })

  it('Data Sources & Integrations states that connection health is not live', () => {
    render(withProviders(<DataSourcesIntegrations />))
    expect(screen.getByText(/not this platform's actual integration state/)).toBeInTheDocument()
    expect(screen.getByText(/no external system integration capability yet/)).toBeInTheDocument()
  })

  it('Platform Governance states that its policies are not enforced by the platform', () => {
    render(withProviders(<PlatformGovernance />))
    expect(screen.getByText(/not policy this platform enforces/)).toBeInTheDocument()
  })

  it('Audit & Change History states that its ledger is not a real audit record', () => {
    render(withProviders(<AuditChangeHistory />))
    expect(screen.getByText(/not a real audit record/)).toBeInTheDocument()
    expect(screen.getByText(/do not refer to real accounts or real events/)).toBeInTheDocument()
  })

  it('still shows the honest empty state, with no disclosure to make, when a section genuinely has no entries', () => {
    render(withProviders(<AuditChangeHistory entries={[]} />))
    expect(screen.getByText('No administrative actions have been recorded yet')).toBeInTheDocument()
    expect(screen.queryByText(/not a real audit record/)).not.toBeInTheDocument()
  })
})
