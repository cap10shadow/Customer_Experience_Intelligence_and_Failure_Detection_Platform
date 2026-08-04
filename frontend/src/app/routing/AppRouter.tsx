// This file is router configuration, not a component module -- it
// necessarily exports `router` alongside the lazy-loaded workspace
// bindings, which react-refresh's single-component-export rule doesn't
// model (fast refresh isn't meaningful for a route table anyway).
/* eslint-disable react-refresh/only-export-components */
import { lazy } from 'react'
import { createBrowserRouter } from 'react-router-dom'

import { AppShell } from '@/app/layouts/AppShell'

import { ROUTE_PATHS } from './routePaths'

const DashboardWorkspace = lazy(() =>
  import('@/workspaces/dashboard').then((module) => ({ default: module.DashboardWorkspace })),
)
const ActionCenterWorkspace = lazy(() =>
  import('@/workspaces/action-center').then((module) => ({ default: module.ActionCenterWorkspace })),
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
  {
    path: '/',
    element: <AppShell />,
    children: [
      { index: true, element: <DashboardWorkspace /> },
      { path: ROUTE_PATHS.actionCenter, element: <ActionCenterWorkspace /> },
      { path: ROUTE_PATHS.investigations, element: <InvestigationsWorkspace /> },
      { path: ROUTE_PATHS.recommendations, element: <RecommendationsWorkspace /> },
      { path: ROUTE_PATHS.analytics, element: <AnalyticsWorkspace /> },
      { path: ROUTE_PATHS.administration, element: <AdministrationWorkspace /> },
    ],
  },
])
