import { Badge } from '@/shared/components/utility'

export interface AdministrationStatusBadgeProps {
  /** Whether this section is backed by a real Gateway/backend capability (Platform Overview, Intelligence Configuration) or is presentation-only illustrative copy (the other four sections) -- see each section's own `AdvisoryNotice` for the full disclosure this badge makes scannable. */
  isLive: boolean
}

/**
 * Separates "real controls" from clearly-marked future/illustrative
 * capability at a glance, next to each section's own title -- never
 * inside a paragraph a reader might skip. Deliberately avoids "live" (and
 * "real-time"/"monitoring") -- ADM-004 forbids Administration reading as
 * an operational monitoring surface, and AdministrationWorkspace's own
 * test suite asserts none of those words ever appears here, so "Real
 * data" is used instead of the more obvious "Live".
 */
export function AdministrationStatusBadge({ isLive }: AdministrationStatusBadgeProps) {
  return <Badge tone={isLive ? 'success' : 'neutral'}>{isLive ? 'Real data' : 'Not yet operational'}</Badge>
}
