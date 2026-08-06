import { useContext } from 'react'

import { RecommendationContext, type RecommendationContextValue } from './RecommendationContext'

export function useRecommendationContext(): RecommendationContextValue {
  const context = useContext(RecommendationContext)
  if (!context) {
    throw new Error('useRecommendationContext must be used within a RecommendationContextProvider')
  }
  return context
}
