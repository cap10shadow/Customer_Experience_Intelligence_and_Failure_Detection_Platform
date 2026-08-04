import styles from './DashboardSubsectionHeading.module.css'

export interface DashboardSubsectionHeadingProps {
  title: string
  description?: string
}

/**
 * A subsection heading with no landmark region attached -- used inside
 * Operational Brief instead of nesting a full `SectionContainer` per
 * subsection. Five nested `<section aria-labelledby>` landmarks inside
 * one Operational Brief section fragmented screen-reader region
 * navigation without adding real structure (a subsection is not an
 * independently navigable area of the page, unlike the four top-level
 * Dashboard sections, which correctly keep their `SectionContainer`
 * landmark). Heading hierarchy is preserved via a real `<h3>`; only the
 * landmark wrapper is removed. Matches the pattern `DecisionOpportunityCard`
 * and `OperationalStoryCard` already use correctly (a heading, no `<section>`).
 */
export function DashboardSubsectionHeading({ title, description }: DashboardSubsectionHeadingProps) {
  return (
    <div>
      <h3 className={styles.heading}>{title}</h3>
      {description ? <p className={styles.description}>{description}</p> : null}
    </div>
  )
}
