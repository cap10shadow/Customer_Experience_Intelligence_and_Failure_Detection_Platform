import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'

import { PartialFailureNotice } from '@/shared/components/feedback'

describe('PartialFailureNotice', () => {
  it('renders nothing when warnings is undefined', () => {
    const { container } = render(<PartialFailureNotice warnings={undefined} />)
    expect(container).toBeEmptyDOMElement()
  })

  it('renders nothing when warnings is an empty array', () => {
    const { container } = render(<PartialFailureNotice warnings={[]} />)
    expect(container).toBeEmptyDOMElement()
  })

  it('renders every warning as a non-blocking, polite status notice when present', () => {
    render(
      <PartialFailureNotice
        warnings={['Recommendation data is temporarily unavailable.', 'Root cause for incident 1 is temporarily unavailable.']}
      />,
    )

    const status = screen.getByRole('status')
    expect(status).toBeInTheDocument()
    expect(screen.getByText('Recommendation data is temporarily unavailable.')).toBeInTheDocument()
    expect(screen.getByText('Root cause for incident 1 is temporarily unavailable.')).toBeInTheDocument()
  })
})
