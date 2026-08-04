import { useEffect, type ReactNode } from 'react'

import { PageHeader } from './PageHeader'

export interface WorkspaceHeaderProps {
  title: string
  description?: string
  actions?: ReactNode
}

const PLATFORM_NAME = 'Operational Intelligence Platform'

/**
 * The single h1 every workspace renders exactly once, at the top of its
 * content -- the anchor every SectionContainer's h2 sits under, keeping
 * heading hierarchy correct application-wide. Also owns `document.title`,
 * so the browser tab and screen-reader page-load announcement always
 * match what's on screen, without every workspace re-implementing it.
 */
export function WorkspaceHeader({ title, description, actions }: WorkspaceHeaderProps) {
  useEffect(() => {
    document.title = `${title} · ${PLATFORM_NAME}`
  }, [title])

  return <PageHeader title={title} description={description} actions={actions} headingLevel={1} />
}
