import { Link } from 'react-router-dom'

import { AdvisoryNotice } from '@/shared/components/feedback'
import { Badge } from '@/shared/components/utility'
import { buildInvestigationPath, buildRecommendationPath } from '@/app/routing/routePaths'
import { classNames } from '@/shared/utilities/classNames'

import type { CopilotAssistantTranscriptMessage, CopilotTranscriptMessage } from '../hooks/useCopilotConversation'
import type { CopilotRelatedEntity, CopilotVisualizationHint } from '../api/types'
import styles from './CopilotMessage.module.css'

/**
 * Copilot's backend falls back to a real, honest `NullLLMProvider` when no
 * `LLM_PROVIDER` is configured (backend/services/copilot_service/app/
 * services/orchestrator/llm_provider.py) -- it returns this exact
 * limitation sentence rather than fabricating an answer. Rendered here as a
 * distinct system notice, not as ordinary assistant prose, so it reads as
 * "the platform is telling you something about its own configuration," not
 * as an AI-generated response.
 */
const NO_LLM_LIMITATION_MARKER = 'No LLM provider is configured'

function isNoLlmMessage(message: CopilotAssistantTranscriptMessage): boolean {
  return message.limitations.some((limitation) => limitation.includes(NO_LLM_LIMITATION_MARKER))
}

const VISUALIZATION_LABEL: Record<CopilotVisualizationHint, string> = {
  trend: 'Related to a trend',
  distribution: 'Related to a distribution',
  comparison: 'Related to a comparison',
  table: 'Related to tabular data',
}

/**
 * Related-entity navigation is only ever built from this repository's own
 * existing routes (`routePaths.ts`) -- never a new route invented for
 * Copilot (Batch 5 implementation prompt §26). Only `incident` and
 * `recommendation` have a real existing detail page; every other
 * `sourceType`/`relatedEntities[].type` value (`root_cause`,
 * `business_impact`, `anomaly`, `trend`, `configuration`) has no detail
 * route in this frontend, so it renders as plain, honest text instead of
 * a fabricated link.
 */
function buildEntityPath(entity: CopilotRelatedEntity): string | null {
  if (entity.type === 'incident') return buildInvestigationPath(entity.id)
  if (entity.type === 'recommendation') return buildRecommendationPath(entity.id)
  return null
}

function RelatedEntityItem({ entity }: { entity: CopilotRelatedEntity }) {
  const path = buildEntityPath(entity)
  const label = `${entity.type}: ${entity.id}`
  if (path) {
    return (
      <Link to={path} className={styles.entityLink}>
        {label}
      </Link>
    )
  }
  return <span className={styles.entityPlain}>{label}</span>
}

function EvidenceCard({
  evidence,
}: {
  evidence: CopilotAssistantTranscriptMessage['evidenceReferences'][number]
}) {
  return (
    <li className={styles.evidenceCard}>
      <span className={styles.evidenceSource}>{evidence.sourceType.replace(/_/g, ' ')}</span>
      <span className={styles.evidenceId}>{evidence.sourceId}</span>
      {evidence.authority ? <span className={styles.evidenceAuthority}>Source: {evidence.authority}</span> : null}
      {evidence.timestamp ? <span className={styles.evidenceTimestamp}>{evidence.timestamp}</span> : null}
    </li>
  )
}

function AssistantMessage({ message }: { message: CopilotAssistantTranscriptMessage }) {
  const visualizationLabel = message.visualizationHint ? VISUALIZATION_LABEL[message.visualizationHint] : null

  if (isNoLlmMessage(message)) {
    return (
      <div className={classNames(styles.bubble, styles.systemNotice)}>
        <AdvisoryNotice
          title="Copilot is not configured in this environment"
          description="Dataset context is available, but no language model is currently connected, so Copilot cannot interpret or answer this question. An operator can configure a language model provider to enable it."
        />
      </div>
    )
  }

  return (
    <div className={classNames(styles.bubble, styles.assistantBubble)}>
      {/* Plain, escaped text only -- Copilot content is untrusted model
          output (Batch 5 implementation prompt §30/§31); no markdown/HTML
          rendering pipeline exists in this repository, so this
          deliberately never uses dangerouslySetInnerHTML. Newlines from
          the backend's own text are preserved via CSS (white-space:
          pre-wrap in the stylesheet), not by parsing any markup. */}
      <p className={styles.answerText}>{message.content}</p>

      {message.keyFindings.length > 0 ? (
        <ul className={styles.findingsList}>
          {message.keyFindings.map((finding) => (
            <li key={finding}>{finding}</li>
          ))}
        </ul>
      ) : null}

      {visualizationLabel ? (
        <div className={styles.visualizationHint}>
          <Badge tone="info">{visualizationLabel}</Badge>
        </div>
      ) : null}

      {message.evidenceReferences.length > 0 ? (
        <ul className={styles.evidenceList}>
          {message.evidenceReferences.map((evidence) => (
            <EvidenceCard key={evidence.evidenceId} evidence={evidence} />
          ))}
        </ul>
      ) : null}

      {message.relatedEntities.length > 0 ? (
        <div className={styles.relatedEntities}>
          {message.relatedEntities.map((entity) => (
            <RelatedEntityItem key={`${entity.type}:${entity.id}`} entity={entity} />
          ))}
        </div>
      ) : null}

      {message.limitations.length > 0 ? (
        <ul className={styles.limitationsList}>
          {message.limitations.map((limitation) => (
            <li key={limitation}>{limitation}</li>
          ))}
        </ul>
      ) : null}
    </div>
  )
}

export function CopilotMessage({ message }: { message: CopilotTranscriptMessage }) {
  if (message.role === 'user') {
    return (
      <div className={classNames(styles.bubble, styles.userBubble)}>
        <p className={styles.answerText}>{message.content}</p>
      </div>
    )
  }
  return <AssistantMessage message={message} />
}
