import { useContext } from 'react'

import { InvestigationContext, type InvestigationContextValue } from './InvestigationContext'

/** Every Investigation component reads shared reading-session state through here instead of holding its own. */
export function useInvestigationContext(): InvestigationContextValue {
  const context = useContext(InvestigationContext)
  if (!context) {
    throw new Error('useInvestigationContext must be used within an InvestigationContextProvider')
  }
  return context
}
