import { describe, expect, it } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import { UserMenu } from '@/shared/components/navigation'

const ITEMS = [
  { label: 'Profile', onSelect: () => {} },
  { label: 'Sign out', onSelect: () => {} },
]

describe('UserMenu keyboard accessibility', () => {
  it('opens via the trigger with correct menu semantics', async () => {
    const user = userEvent.setup()
    render(<UserMenu userName="Operations User" items={ITEMS} />)

    const trigger = screen.getByRole('button', { name: /Operations User/ })
    expect(trigger).toHaveAttribute('aria-haspopup', 'menu')
    expect(trigger).toHaveAttribute('aria-expanded', 'false')

    await user.click(trigger)

    expect(trigger).toHaveAttribute('aria-expanded', 'true')
    expect(screen.getByRole('menu')).toBeInTheDocument()
    expect(screen.getAllByRole('menuitem')).toHaveLength(ITEMS.length)
  })

  it('closes on Escape and returns focus to the trigger', async () => {
    const user = userEvent.setup()
    render(<UserMenu userName="Operations User" items={ITEMS} />)

    const trigger = screen.getByRole('button', { name: /Operations User/ })
    await user.click(trigger)
    expect(screen.getByRole('menu')).toBeInTheDocument()

    await user.keyboard('{Escape}')

    await waitFor(() => expect(screen.queryByRole('menu')).not.toBeInTheDocument())
    expect(trigger).toHaveFocus()
  })

  it('closes on outside click', async () => {
    const user = userEvent.setup()
    render(
      <div>
        <UserMenu userName="Operations User" items={ITEMS} />
        <button type="button">Outside</button>
      </div>,
    )

    await user.click(screen.getByRole('button', { name: /Operations User/ }))
    expect(screen.getByRole('menu')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Outside' }))
    await waitFor(() => expect(screen.queryByRole('menu')).not.toBeInTheDocument())
  })
})
