import { useState } from 'react'
import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'

import { Sidebar } from '@/shared/components/navigation'
import { useDisclosure } from '@/shared/hooks/useDisclosure'

function ControlledSidebar() {
  const [isCollapsed, setIsCollapsed] = useState(false)
  const mobileNav = useDisclosure()
  return (
    <MemoryRouter>
      <Sidebar
        isCollapsed={isCollapsed}
        onToggleCollapse={() => setIsCollapsed((current) => !current)}
        isMobileOpen={mobileNav.isOpen}
        onCloseMobile={mobileNav.close}
      />
      <button type="button" onClick={mobileNav.open}>
        Open mobile nav
      </button>
    </MemoryRouter>
  )
}

describe('Sidebar', () => {
  it('toggles collapsed state and reflects it via aria-pressed', async () => {
    const user = userEvent.setup()
    render(<ControlledSidebar />)

    const toggle = screen.getByRole('button', { name: 'Collapse navigation' })
    expect(toggle).toHaveAttribute('aria-pressed', 'false')

    await user.click(toggle)

    expect(screen.getByRole('button', { name: 'Expand navigation' })).toHaveAttribute('aria-pressed', 'true')
  })

  it('opens the mobile drawer with a dismissible scrim', async () => {
    const user = userEvent.setup()
    render(<ControlledSidebar />)

    expect(screen.queryByRole('button', { name: 'Close navigation' })).not.toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Open mobile nav' }))

    const scrim = screen.getByRole('button', { name: 'Close navigation' })
    expect(scrim).toBeInTheDocument()

    await user.click(scrim)
    expect(screen.queryByRole('button', { name: 'Close navigation' })).not.toBeInTheDocument()
  })
})
