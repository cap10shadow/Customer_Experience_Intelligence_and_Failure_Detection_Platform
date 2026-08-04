import { describe, expect, it } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import { ThemeProvider } from '@/app/theme/ThemeProvider'
import { useTheme } from '@/app/theme/useTheme'

function ThemeProbe() {
  const { mode, resolvedTheme, setMode } = useTheme()
  return (
    <div>
      <span data-testid="mode">{mode}</span>
      <span data-testid="resolved">{resolvedTheme}</span>
      <button type="button" onClick={() => setMode('dark')}>
        Set dark
      </button>
    </div>
  )
}

describe('ThemeProvider', () => {
  it('defaults to system mode and applies no explicit data-theme override', () => {
    render(
      <ThemeProvider>
        <ThemeProbe />
      </ThemeProvider>,
    )
    expect(screen.getByTestId('mode')).toHaveTextContent('system')
    expect(document.documentElement.dataset.theme).toBeUndefined()
  })

  it('applies an explicit data-theme attribute when mode is set to dark', async () => {
    const user = userEvent.setup()
    render(
      <ThemeProvider>
        <ThemeProbe />
      </ThemeProvider>,
    )

    await user.click(screen.getByRole('button', { name: 'Set dark' }))

    await waitFor(() => {
      expect(screen.getByTestId('resolved')).toHaveTextContent('dark')
    })
    expect(document.documentElement.dataset.theme).toBe('dark')
  })
})
