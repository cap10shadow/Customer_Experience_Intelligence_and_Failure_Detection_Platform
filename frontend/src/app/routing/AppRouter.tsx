// This file is router configuration, not a component module -- it
// necessarily exports `router` alongside the lazy-loaded workspace
// bindings, which react-refresh's single-component-export rule doesn't
// model (fast refresh isn't meaningful for a route table anyway).
/* eslint-disable react-refresh/only-export-components */
import { lazy } from 'react'
import { createBrowserRouter } from 'react-router-dom'

import { AppShell } from '@/app/layouts/AppShell'
import { LoginPage } from '@/auth/components/LoginPage'
import { RequireAuth } from '@/auth/components/RequireAuth'

import { ROUTE_PATHS, ROUTE_TEMPLATES } from './routePaths'

const DashboardWorkspace = lazy(() =>
  import('@/workspaces/dashboard').then((module) => ({ default: module.DashboardWorkspace })),
)
const InvestigationsWorkspace = lazy(() =>
  import('@/workspaces/investigations').then((module) => ({ default: module.InvestigationsWorkspace })),
)
const RecommendationsWorkspace = lazy(() =>
  import('@/workspaces/recommendations').then((module) => ({ default: module.RecommendationsWorkspace })),
)
const AnalyticsWorkspace = lazy(() =>
  import('@/workspaces/analytics').then((module) => ({ default: module.AnalyticsWorkspace })),
)
const AdministrationWorkspace = lazy(() =>
  import('@/workspaces/administration').then((module) => ({ default: module.AdministrationWorkspace })),
)

/**
 * `WorkspaceLayout` (mounted once inside `AppShell`) already wraps every
 * routed element in `Suspense`/`ErrorBoundary`, so route elements below
 * only need the lazy component itself -- no per-route fallback wiring.
 */
export const router = createBrowserRouter([
  // Phase 13 Batch 2 (AD-6): the one route outside RequireAuth/AppShell
  // -- a signed-out visitor must be able to reach it without already
  // having a session.
  { path: ROUTE_PATHS.login, element: <LoginPage /> },
  {
    path: '/',
    element: (
      <RequireAuth>
        <AppShell />
      </RequireAuth>
    ),
    children: [
      { index: true, element: <DashboardWorkspace /> },
      { path: ROUTE_TEMPLATES.investigation, element: <InvestigationsWorkspace /> },
      { path: ROUTE_TEMPLATES.recommendation, element: <RecommendationsWorkspace /> },
      { path: ROUTE_PATHS.analytics, element: <AnalyticsWorkspace /> },
      { path: ROUTE_PATHS.administration, element: <AdministrationWorkspace /> },
    ],
  },
])
