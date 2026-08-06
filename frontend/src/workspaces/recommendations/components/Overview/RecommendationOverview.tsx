import { RecommendationSection } from '../foundation'
import type { RecommendationOverview as RecommendationOverviewData } from '../../types'
import { RecommendationOverviewCard } from './RecommendationOverviewCard'

const OVERVIEW: RecommendationOverviewData = {
  headline: 'Review the recent payment provider change',
  summary:
    'A recent change on the payment provider side lines up closely with the checkout failures described in the related investigation. Reviewing that change would confirm or rule out the suspected cause.',
  category: 'Investigate',
  priority: 'High',
}

export interface RecommendationOverviewProps {
  isLoading?: boolean
}

/** "What is being recommended?" -- the canonical detail view; Investigation's own transition card only ever summarized this to invite the reader here. */
export function RecommendationOverview({ isLoading = false }: RecommendationOverviewProps) {
  return (
    <RecommendationSection id="overview" title="Recommendation Overview" description="What is being recommended?">
      <RecommendationOverviewCard overview={OVERVIEW} isLoading={isLoading} />
    </RecommendationSection>
  )
}
