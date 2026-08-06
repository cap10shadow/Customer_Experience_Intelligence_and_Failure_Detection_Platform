import type { StatusTone } from '@/shared/components/utility'

/**
 * The human decision itself -- a single, bounded judgment call, distinct
 * from the recommendation's ongoing `LifecycleStage` below. Per Decision
 * Before Lifecycle: a recommendation stays 'pending-review' until a
 * human makes this call; nothing about its lifecycle exists before that.
 */
export type DecisionStatus = 'pending-review' | 'approved' | 'rejected' | 'deferred'

export const DECISION_STATUS_LABEL: Record<DecisionStatus, string> = {
  'pending-review': 'Pending Review',
  approved: 'Approved',
  rejected: 'Rejected',
  deferred: 'Deferred',
}

/**
 * The single source of truth `RecommendationNavigator` and
 * `DecisionSummary` both consume -- 'rejected' deliberately shares the
 * same neutral tone as 'pending-review' and 'deferred'; only 'approved'
 * uses the success tone, since a past decision is informational, never
 * an alarm (UX-002's Calm Software constraint applies here too, not
 * only to Risk Assessment).
 */
export const DECISION_STATUS_TONE: Record<DecisionStatus, StatusTone> = {
  'pending-review': 'neutral',
  approved: 'success',
  rejected: 'neutral',
  deferred: 'neutral',
}

export interface DecisionRecord {
  status: DecisionStatus
  /** Illustrative framing only -- never a real audit trail in this step. */
  note: string
}

/**
 * Lifecycle only ever exists once a recommendation is Approved --
 * Rejected and Deferred recommendations are represented by
 * `DecisionStatus` alone and never reach this progression. Awaiting
 * Implementation and Outcome Evaluation deliberately mirror the
 * long-term Human Action / Outcome vision (ARB-002) using
 * workspace-appropriate names, without claiming to implement either.
 */
export type LifecycleStage = 'awaiting-implementation' | 'outcome-evaluation' | 'completed'

export const LIFECYCLE_STAGE_ORDER: LifecycleStage[] = ['awaiting-implementation', 'outcome-evaluation', 'completed']

export const LIFECYCLE_STAGE_LABEL: Record<LifecycleStage, string> = {
  'awaiting-implementation': 'Awaiting Implementation',
  'outcome-evaluation': 'Outcome Evaluation',
  completed: 'Completed',
}

export interface RecommendationOverview {
  headline: string
  summary: string
  category: string
  priority: string
}

export interface RationaleReason {
  headline: string
  explanation: string
}

export interface OutcomeItem {
  id: string
  headline: string
  detail: string
}

export interface RiskItem {
  id: string
  headline: string
  detail: string
}
