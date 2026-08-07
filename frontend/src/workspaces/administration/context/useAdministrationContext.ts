import { useContext } from 'react'

import { AdministrationContext, type AdministrationContextValue } from './AdministrationContext'

export function useAdministrationContext(): AdministrationContextValue {
  const context = useContext(AdministrationContext)
  if (!context) {
    throw new Error('useAdministrationContext must be used within an AdministrationContextProvider')
  }
  return context
}
