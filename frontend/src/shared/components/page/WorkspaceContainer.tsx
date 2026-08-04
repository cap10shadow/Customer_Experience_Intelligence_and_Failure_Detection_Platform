import type { ReactNode } from 'react'

import { Stack } from '@/shared/components/layout'

import { ContentContainer } from './ContentContainer'
import { WorkspaceHeader, type WorkspaceHeaderProps } from './WorkspaceHeader'

export interface WorkspaceContainerProps extends WorkspaceHeaderProps {
  children: ReactNode
}

/**
 * The top-level composition every workspace root component renders:
 * width-capped content, the workspace's one `<h1>` (via WorkspaceHeader),
 * and its sections stacked below. Every one of the six workspaces
 * (Dashboard, Action Center, Investigations, Recommendations, Analytics,
 * Administration) starts from this same component -- new workspaces in
 * future phases extend it rather than reinventing page structure.
 */
export function WorkspaceContainer({ title, description, actions, children }: WorkspaceContainerProps) {
  return (
    <ContentContainer>
      <Stack gap={8}>
        <WorkspaceHeader title={title} description={description} actions={actions} />
        {children}
      </Stack>
    </ContentContainer>
  )
}
