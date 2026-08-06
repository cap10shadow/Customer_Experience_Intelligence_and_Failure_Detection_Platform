import { StatusIndicator, type StatusTone } from '@/shared/components/utility'

import type { ConfidenceLevel } from '../../types'

const LEVEL_TONE: Record<ConfidenceLevel, StatusTone> = {
  low: 'warning',
  moderate: 'info',
  high: 'success',
}

const LEVEL_LABEL: Record<ConfidenceLevel, string> = {
  low: 'Low confidence',
  moderate: 'Moderate confidence',
  high: 'High confidence',
}

export interface ConfidencePresentationProps {
  level: ConfidenceLevel
  /**
   * What this specific value measures -- e.g. "root cause rule
   * certainty" or "business impact data completeness". Always required
   * and always rendered: per ARB-008, confidence is stage-specific and
   * two confidence values must never be shown without saying what each
   * one actually means. This component's job is presentation
   * consistency (one shared visual language for "how sure are we"),
   * never a shared calculation -- it accepts a level the caller already
   * computed, it never derives one.
   */
  measures: string
}

/**
 * Renders "{Level} confidence — {what it measures}" as one inseparable
 * unit, and reuses `StatusIndicator`'s distinct-icon-per-tone so
 * confidence is never conveyed by color alone. Deliberately cannot be
 * rendered with a level and no `measures` string -- that omission is
 * exactly how two incomparable confidence values end up looking like
 * one universal score.
 */
export function ConfidencePresentation({ level, measures }: ConfidencePresentationProps) {
  return <StatusIndicator tone={LEVEL_TONE[level]} label={`${LEVEL_LABEL[level]} — ${measures}`} />
}
