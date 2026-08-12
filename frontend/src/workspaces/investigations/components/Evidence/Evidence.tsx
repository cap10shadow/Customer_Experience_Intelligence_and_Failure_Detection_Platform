import { InvestigationEmptyState, InvestigationSection } from '../foundation'
import type { EvidenceItem } from '../../types'
import { EvidenceGroup } from './EvidenceGroup'

const DEFAULT_EVIDENCE_ITEMS: EvidenceItem[] = [
  {
    id: 'nlp-complaint-cluster',
    headline: 'A cluster of complaints mentions failed payments at checkout',
    detail: 'Multiple recent complaints independently describe the same failure point.',
    source: 'NLP Intelligence',
  },
  {
    id: 'anomaly-spike',
    headline: 'Checkout failure rate registered as a statistical anomaly',
    detail: 'The rate moved outside its expected range for this time window.',
    source: 'Anomaly Detection',
  },
  {
    id: 'incident-correlation',
    headline: 'Related anomalies were grouped into a single incident',
    detail: 'Anomalies in the same region and category were correlated rather than treated as separate events.',
    source: 'Incident Correlation',
  },
]

export interface EvidenceProps {
  /** Defaults to illustrative content -- InvestigationsWorkspace passes real, Gateway-sourced evidence here instead of editing this component. */
  items?: EvidenceItem[]
  isLoading?: boolean
}

/**
 * "Why should I believe this investigation?" -- every claim the later
 * sections make traces back to one of these cards. Never draws a
 * conclusion itself; Root Cause Analysis is the first section allowed
 * to do that, and only after this one.
 */
export function Evidence({ items = DEFAULT_EVIDENCE_ITEMS, isLoading = false }: EvidenceProps) {
  return (
    <InvestigationSection
      id="evidence"
      title="Evidence"
      description="Why should I believe this investigation?"
    >
      {!isLoading && items.length === 0 ? (
        <InvestigationEmptyState
          title="No evidence gathered yet"
          description="This investigation hasn't collected supporting evidence for this stage yet. Evidence appears here as soon as an upstream intelligence stage contributes it."
        />
      ) : (
        <EvidenceGroup items={items} isLoading={isLoading} />
      )}
    </InvestigationSection>
  )
}
