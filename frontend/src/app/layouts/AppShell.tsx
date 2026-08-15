import { useState } from 'react'
import { Outlet, useLocation, useNavigate } from 'react-router-dom'

import { PRIMARY_NAVIGATION } from '@/app/configuration/navigation.config'
import { ROUTE_PATHS } from '@/app/routing/routePaths'
import { useAuth } from '@/auth/context/AuthContext'
import { Copilot } from '@/copilot'
import { Sidebar, TopBar } from '@/shared/components/navigation'
import { useDisclosure } from '@/shared/hooks/useDisclosure'

import { WorkspaceLayout } from './WorkspaceLayout'
import styles from './AppShell.module.css'

const SIDEBAR_COLLAPSED_STORAGE_KEY = 'oi-platform:sidebar-collapsed'

function getActiveWorkspaceLabel(pathname: string): string {
  const match = PRIMARY_NAVIGATION.find((item) => (item.path === '/' ? pathname === '/' : pathname.startsWith(item.path)))
  return match?.label ?? 'Operational Intelligence Platform'
}

/**
 * The persistent application frame -- rendered exactly once at the router
 * root. Owns the Sidebar and TopBar (they never remount between
 * workspaces); only the `<main>` region's content changes as the user
 * navigates, via `WorkspaceLayout`'s `<Outlet />`.
 */
export function AppShell() {
  const location = useLocation()
  const navigate = useNavigate()
  const { user, logout } = useAuth()
  const [isCollapsed, setIsCollapsed] = useState(
    () => typeof window !== 'undefined' && window.localStorage.getItem(SIDEBAR_COLLAPSED_STORAGE_KEY) === 'true',
  )
  const mobileNav = useDisclosure()

  // AppShell only ever renders inside RequireAuth (see AppRouter.tsx),
  // so `user` is always non-null here in practice -- the fallback below
  // exists only so TopBar's prop type stays a plain `string`, not to
  // handle a real anonymous-render case.
  const handleSignOut = async () => {
    await logout()
    navigate(ROUTE_PATHS.login, { replace: true })
  }

  const toggleCollapsed = () => {
    setIsCollapsed((current) => {
      const next = !current
      window.localStorage.setItem(SIDEBAR_COLLAPSED_STORAGE_KEY, String(next))
      return next
    })
  }

  const activeLabel = getActiveWorkspaceLabel(location.pathname)

  return (
    <div className={styles.shell}>
      <a href="#main-content" className={styles.skipLink}>
        Skip to main content
      </a>
      <Sidebar
        isCollapsed={isCollapsed}
        onToggleCollapse={toggleCollapsed}
        isMobileOpen={mobileNav.isOpen}
        onCloseMobile={mobileNav.close}
      />
      <div className={styles.column}>
        <TopBar
          breadcrumbSegments={[{ label: activeLabel }]}
          onOpenMobileNav={mobileNav.open}
          userName={user?.email ?? 'Signed in'}
          onSignOut={handleSignOut}
        />
        <main id="main-content" className={styles.main} tabIndex={-1}>
          <WorkspaceLayout>
            <Outlet />
          </WorkspaceLayout>
        </main>
      </div>
      {/* Mounted once, application-wide, as a sibling of the routed
          content -- never per-workspace (architecture §4/§32). */}
      <Copilot />
    </div>
  )
}
