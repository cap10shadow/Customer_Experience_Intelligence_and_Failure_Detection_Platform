import { describe, expect, it } from 'vitest'

import { deriveWorkspaceContext } from '@/copilot/context/deriveWorkspaceContext'

describe('deriveWorkspaceContext', () => {
  it('identifies the dashboard workspace at the root path', () => {
    expect(deriveWorkspaceContext('/')).toEqual({ workspace: 'dashboard' })
  })

  it('identifies the investigations workspace and extracts incidentId from the route', () => {
    expect(deriveWorkspaceContext('/investigations/INC-123')).toEqual({
      workspace: 'investigations',
      incidentId: 'INC-123',
    })
  })

  it('identifies the investigations workspace with no incidentId when none is in the route', () => {
    expect(deriveWorkspaceContext('/investigations')).toEqual({ workspace: 'investigations' })
  })

  it('identifies the recommendations workspace and extracts recommendationId from the route', () => {
    expect(deriveWorkspaceContext('/recommendations/rec-1')).toEqual({
      workspace: 'recommendations',
      recommendationId: 'rec-1',
    })
  })

  it('identifies the recommendations workspace with no recommendationId when none is in the route', () => {
    expect(deriveWorkspaceContext('/recommendations')).toEqual({ workspace: 'recommendations' })
  })

  it('identifies the analytics workspace', () => {
    expect(deriveWorkspaceContext('/analytics')).toEqual({ workspace: 'analytics' })
  })

  it('identifies the administration workspace', () => {
    expect(deriveWorkspaceContext('/administration')).toEqual({ workspace: 'administration' })
  })

  it('decodes a URL-encoded incidentId', () => {
    expect(deriveWorkspaceContext('/investigations/INC%2F1')).toEqual({
      workspace: 'investigations',
      incidentId: 'INC/1',
    })
  })

  it('never includes filters or timeRange -- not derivable at the AppShell mount level', () => {
    const context = deriveWorkspaceContext('/')
    expect(context).not.toHaveProperty('filters')
    expect(context).not.toHaveProperty('timeRange')
  })
})
