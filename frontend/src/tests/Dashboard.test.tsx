import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'

import { DashboardWorkspace } from '@/workspaces/dashboard'

function renderDashboard() {
  return render(
    <MemoryRouter>
      <DashboardWorkspace />
    </MemoryRouter>,
  )
}

describe('DashboardWorkspace composition', () => {
  it('renders one workspace heading and the four architectural sections in fixed order', () => {
    renderDashboard()

    expect(screen.getByRole('heading', { level: 1, name: 'Operational Intelligence Dashboard' })).toBeInTheDocument()

    const sectionHeadings = screen.getAllByRole('heading', { level: 2 }).map((heading) => heading.textContent)
    expect(sectionHeadings).toEqual([
      'Operational brief',
      'Decision summary',
      'Investigation entry points',
      'Supporting evidence',
    ])
  })

  it('renders every Operational Brief subsection as a nested level-3 heading', () => {
    renderDashboard()

    const subsectionHeadings = screen.getAllByRole('heading', { level: 3 }).map((heading) => heading.textContent)
    expect(subsectionHeadings).toEqual(
      expect.arrayContaining([
        'Overall operational status',
        'Critical situations',
        'Key changes',
        'Recommended focus',
        'Operational health snapshot',
      ]),
    )
  })

  it('communicates stability confidently by default rather than manufacturing urgency', () => {
    renderDashboard()

    expect(screen.getByText('Operations Stable')).toBeInTheDocument()
    expect(screen.getByText('No critical situations')).toBeInTheDocument()
    expect(screen.getByText('No meaningful changes')).toBeInTheDocument()
    expect(screen.queryByText(/no data/i)).not.toBeInTheDocument()
  })

  it('surfaces Decision Opportunities as judgment calls, not a task or alert list', () => {
    renderDashboard()

    expect(screen.getByRole('heading', { name: 'Approve recommendation' })).toBeInTheDocument()
    expect(screen.getByText(/High business importance/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Review recommendation/ })).toHaveAttribute('href', '/recommendations')
  })

  it('presents Investigation Entry Points as Operational Stories with a drill-down, not raw incident records', () => {
    renderDashboard()

    expect(screen.getByRole('heading', { name: 'Payment reliability deteriorating' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Investigate this story/ })).toHaveAttribute('href', '/investigations')
  })

  it('presents Supporting Evidence as organized future-analytics placeholders, not charts', () => {
    renderDashboard()

    expect(screen.getByText('Operational trends')).toBeInTheDocument()
    expect(screen.getByText('Regional comparison')).toBeInTheDocument()
    expect(screen.getByText('Sentiment trend')).toBeInTheDocument()
  })

  it('separates every section with a visible boundary, reinforcing one continuous journey', () => {
    renderDashboard()
    expect(document.querySelectorAll('hr').length).toBe(3)
  })
})
