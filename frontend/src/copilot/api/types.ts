/**
 * The public Gateway Copilot contract (camelCase), mirrored field-for-field
 * from `backend/services/gateway_service/app/schemas/copilot.py` -- no
 * field added, none renamed. This is the only Copilot type module the rest
 * of `copilot/` may import from; nothing here reaches into
 * `copilot_service`'s internal snake_case contract.
 */

export type CopilotWorkspaceName = 'dashboard' | 'investigations' | 'recommendations' | 'analytics' | 'administration'

export interface CopilotWorkspaceContext {
  workspace: CopilotWorkspaceName
  incidentId?: string
  recommendationId?: string
  filters?: Record<string, string>
  timeRange?: string
}

export interface CopilotQueryRequest {
  message: string
  conversationId?: string
  workspaceContext?: CopilotWorkspaceContext
}

export interface CopilotEvidenceReference {
  evidenceId: string
  sourceType: string
  sourceId: string
  authority?: string | null
  timestamp?: string | null
}

export interface CopilotRelatedEntity {
  type: string
  id: string
}

export type CopilotVisualizationHint = 'trend' | 'distribution' | 'comparison' | 'table'

export interface CopilotResponse {
  answer: string
  keyFindings: string[]
  evidenceReferences: CopilotEvidenceReference[]
  relatedEntities: CopilotRelatedEntity[]
  visualizationHint?: CopilotVisualizationHint | null
  limitations: string[]
  conversationId: string
  requestId: string
}
