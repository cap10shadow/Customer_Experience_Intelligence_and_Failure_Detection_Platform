import { InvestigationEmptyState, InvestigationSection } from '../foundation'
import type { RootCauseExplanation } from '../../types'
import { RootCauseCard } from './RootCauseCard'

const DEFAULT_ROOT_CAUSE: RootCauseExplanation = {
  headline: 'Most likely cause: a recent payment provider change',
  reasoning:
    'The timing of the checkout failures aligns closely with a recent change on the payment provider side. This is presented as the most likely explanation given the evidence above, not a certainty.',
  confidenceLevel: 'moderate',
}

export interface RootCauseAnalysisProps {
  /**
   * Defaults to illustrative content -- InvestigationsWorkspace passes a
   * real explanation here instead of editing this component. Explicit
   * `null` (as opposed to omitting the prop) means root cause analysis
   * genuinely has not been run for this Incident yet -- a real domain
   * state, rendered as an honest empty state, not the illustrative
   * default.
   */
  explanation?: RootCauseExplanation | null
  isLoading?: boolean
}

/** "Why did this happen?" -- the investigation's first conclusion, and only after Evidence has already been presented. */
export function RootCauseAnalysis({ explanation = DEFAULT_ROOT_CAUSE, isLoading = false }: RootCauseAnalysisProps) {
  return (
    <InvestigationSection id="root-cause" title="Root Cause Analysis" description="Why did this happen?">
      {!isLoading && explanation === null ? (
        <InvestigationEmptyState
          title="Root cause analysis has not been completed yet"
          description="This investigation hasn't identified a likely root cause yet. This section updates as soon as Root Cause Analysis has run for this incident."
        />
      ) : (
        <RootCauseCard explanation={explanation ?? DEFAULT_ROOT_CAUSE} isLoading={isLoading} />
      )}
    </InvestigationSection>
  )
}
