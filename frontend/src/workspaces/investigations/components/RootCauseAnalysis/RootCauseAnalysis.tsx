import { InvestigationSection } from '../foundation'
import type { RootCauseExplanation } from '../../types'
import { RootCauseCard } from './RootCauseCard'

const ROOT_CAUSE: RootCauseExplanation = {
  headline: 'Most likely cause: a recent payment provider change',
  reasoning:
    'The timing of the checkout failures aligns closely with a recent change on the payment provider side. This is presented as the most likely explanation given the evidence above, not a certainty.',
  confidenceLevel: 'moderate',
}

export interface RootCauseAnalysisProps {
  isLoading?: boolean
}

/** "Why did this happen?" -- the investigation's first conclusion, and only after Evidence has already been presented. */
export function RootCauseAnalysis({ isLoading = false }: RootCauseAnalysisProps) {
  return (
    <InvestigationSection id="root-cause" title="Root Cause Analysis" description="Why did this happen?">
      <RootCauseCard explanation={ROOT_CAUSE} isLoading={isLoading} />
    </InvestigationSection>
  )
}
